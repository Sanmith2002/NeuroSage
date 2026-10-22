"""Grad-CAM and QC PNGs, kept in memory only and expired after ARTIFACT_TTL (spec §4, §6.13)."""
from __future__ import annotations

import io
import secrets
import threading
import time

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

CAM_CAPTION = 'Model attention, not a lesion map.'


class ArtifactStore:
    def __init__(self, ttl_s: int = 1800, max_items: int = 200):
        self.ttl_s, self.max_items = ttl_s, max_items
        self._items: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()

    def put(self, png: bytes) -> str:
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._purge()
            self._items[token] = (time.time() + self.ttl_s, png)
            while len(self._items) > self.max_items:
                self._items.pop(next(iter(self._items)))
        return token

    def get(self, token: str) -> bytes | None:
        with self._lock:
            self._purge()
            item = self._items.get(token)
            return item[1] if item else None

    def _purge(self) -> None:
        now = time.time()
        for k in [k for k, (exp, _) in self._items.items() if exp < now]:
            del self._items[k]


def _mid_slices(v: np.ndarray):
    cx, cy, cz = (s // 2 for s in v.shape)
    # sagittal, coronal, axial — rotated so anterior/superior point up in RAS-ordered MNI arrays
    return [np.rot90(v[cx, :, :]), np.rot90(v[:, cy, :]), np.rot90(v[:, :, cz])]


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return buf.getvalue()


def gradcam_png(volume: np.ndarray, cam: np.ndarray, p: float | None = None) -> bytes:
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.6))
    for ax, img, c, title in zip(axes, _mid_slices(volume), _mid_slices(cam), ['Sagittal', 'Coronal', 'Axial']):
        ax.imshow(img, cmap='gray', vmin=-2.5, vmax=2.5)
        ax.imshow(c, cmap='jet', alpha=0.35, vmin=0, vmax=1)
        ax.set_title(title, fontsize=9)
        ax.axis('off')
    head = 'Grad-CAM · clinical-AD fusion model (fold 0)' + (f' · P(AD) {p:.2f}' if p is not None else '')
    fig.suptitle(head, fontsize=10)
    fig.text(0.5, 0.01, CAM_CAPTION, ha='center', fontsize=9, style='italic')
    return _png(fig)


def qc_png(volume: np.ndarray, qc: dict | None) -> bytes:
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.4))
    for ax, img, title in zip(axes, _mid_slices(volume), ['Sagittal', 'Coronal', 'Axial']):
        ax.imshow(img, cmap='gray', vmin=-2.5, vmax=2.5)
        ax.contour(img != 0, levels=[0.5], colors='#2bb673', linewidths=0.6)
        ax.set_title(title, fontsize=9)
        ax.axis('off')
    if qc:
        txt = ' · '.join(f'{k}: {v}' for k, v in qc.items() if k != 'passed')
        fig.text(0.5, 0.01, f'QC — {txt}', ha='center', fontsize=8)
    fig.suptitle('Registered T1 in MNI space (2 mm model input)', fontsize=10)
    return _png(fig)
