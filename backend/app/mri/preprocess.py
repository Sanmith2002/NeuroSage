"""T1 MRI preprocessing: an exact port of Stage 2b + Stage 3 (spec §6).

dcm2niix → HD-BET v2 → N4 → MNI152 affine → 160×192×160 crop → masked z-score → 2 mm (float16 round-trip).
Any deviation changes the model's input distribution, so every parameter lives in PREPROC_SPEC.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

PREPROC_SPEC = {
    'convert': {'tool': 'dcm2niix', 'args': '-z y -b n -f %s', 'pick': 'largest 3D output'},
    'skullstrip': {'tool': 'HD-BET v2', 'args': '--save_bet_mask --no_bet_image --disable_tta', 'min_brain_cm3': 300},
    'bias': {'tool': 'ants.n4_bias_field_correction', 'shrink_factor': 4},
    'template': {'source': 'nilearn load_mni152_template(resolution=1) + load_mni152_brain_mask(resolution=1)'},
    'register': {'primary': 'AffineFast', 'fallback': 'Affine', 'min_dice': 0.85,
                 'fixed': 'template * template_mask', 'moving': 'n4 * mask', 'warp_interp': 'linear',
                 'mask_interp': 'nearestNeighbor'},
    'crop': {'shape': [160, 192, 160], 'lo': [18, 21, 0], 'hi': [178, 213, 160]},
    'normalise': {'method': 'masked z-score', 'eps': 1e-6, 'clip': [-5, 5], 'multiply_by_mask': True},
    'downsample': {'factor': 2, 'method': 'block mean', 'dtype_roundtrip': 'float16', 'output_shape': [80, 96, 80]},
}
CROP = np.array(PREPROC_SPEC['crop']['shape'])
MIN_BRAIN_CM3 = PREPROC_SPEC['skullstrip']['min_brain_cm3']
MIN_DICE = PREPROC_SPEC['register']['min_dice']

Progress = Callable[[str, float], None]


class PipelineError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class Preprocessed:
    x: np.ndarray                         # (80, 96, 80) float32 model input
    qc: dict
    timings_s: dict[str, float] = field(default_factory=dict)


# ------------------------------------------------------------------ template
def template_paths(cache_dir: Path) -> tuple[Path, Path]:
    """Saves the nilearn MNI152 1 mm template and brain mask once, so ANTs reads identical voxels every time."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    t, m = cache_dir / 'mni152_t1_1mm.nii.gz', cache_dir / 'mni152_brainmask_1mm.nii.gz'
    if not (t.exists() and m.exists()):
        from nilearn.datasets import load_mni152_brain_mask, load_mni152_template
        load_mni152_template(resolution=1).to_filename(str(t))
        load_mni152_brain_mask(resolution=1).to_filename(str(m))
    return t, m


def crop_box(template_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tm = template_mask > 0
    nz = np.array(np.nonzero(tm))
    centre = (nz.min(1) + nz.max(1)) // 2
    lo = np.clip(centre - CROP // 2, 0, None)
    hi = lo + CROP
    pad = np.clip(hi - np.array(tm.shape), 0, None)
    lo, hi = lo - pad, hi - pad
    return lo, hi


def check_crop(lo: np.ndarray, hi: np.ndarray) -> None:
    exp_lo, exp_hi = PREPROC_SPEC['crop']['lo'], PREPROC_SPEC['crop']['hi']
    if lo.tolist() != exp_lo or hi.tolist() != exp_hi:
        raise PipelineError('INTERNAL', f'crop box {lo.tolist()}–{hi.tolist()} differs from training {exp_lo}–{exp_hi}')


def _crop(a: np.ndarray, lo, hi) -> np.ndarray:
    return a[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]


def dice(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a > 0.5, b > 0.5
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else 0.0


# ------------------------------------------------------------------ step 1: input
def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    root = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if root not in target.parents and target != root:
            raise PipelineError('BAD_INPUT', 'zip contains unsafe paths')
    zf.extractall(dest)


def to_nifti(src: Path, work: Path) -> Path:
    import nibabel as nib

    name = src.name.lower()
    if name.endswith('.zip'):
        dicom, out = work / 'dicom', work / 'nii'
        dicom.mkdir(); out.mkdir()
        try:
            with zipfile.ZipFile(src) as zf:
                _safe_extract(zf, dicom)
        except zipfile.BadZipFile as e:
            raise PipelineError('BAD_INPUT', 'not a valid zip file') from e
        if shutil.which('dcm2niix') is None:
            raise PipelineError('INTERNAL', 'dcm2niix is not installed on the server')
        r = subprocess.run(['dcm2niix', '-z', 'y', '-b', 'n', '-f', '%s', '-o', str(out), str(dicom)],
                           capture_output=True, text=True)
        cands = []
        for p in out.glob('*.nii*'):
            shape = nib.load(str(p)).shape
            if len(shape) == 3 or (len(shape) == 4 and shape[3] == 1):
                cands.append((int(np.prod(shape[:3])), p))
        if not cands:
            raise PipelineError('BAD_INPUT', 'no 3D volume could be converted from the DICOM series'
                                + ('' if r.returncode == 0 else ' (dcm2niix failed)'))
        nii = max(cands)[1]
    elif name.endswith('.nii') or name.endswith('.nii.gz'):
        nii = src
    else:
        raise PipelineError('BAD_INPUT', 'upload a .nii, .nii.gz or a .zip of one DICOM series')

    try:
        img = nib.load(str(nii))
    except Exception as e:
        raise PipelineError('BAD_INPUT', 'the file could not be read as NIfTI') from e
    shape = img.shape
    if len(shape) == 4 and shape[3] > 1:
        raise PipelineError('BAD_INPUT', '4D / multi-echo volumes are not supported; upload one T1 MPRAGE volume')
    if len(shape) not in (3, 4) or min(shape[:3]) < 32:
        raise PipelineError('BAD_INPUT', f'unexpected volume shape {tuple(shape)}')
    try:
        descrip = np.asarray(img.header['descrip']).tobytes().decode(errors='ignore').strip('\x00 ').lower()
    except (KeyError, TypeError):
        descrip = ''
    if 't1' not in descrip and any(k in descrip for k in ('flair', 't2', 'dwi', 'bold')):
        raise PipelineError('BAD_INPUT', f'header describes a non-T1 series ({descrip.strip()})')
    if len(shape) == 4:   # squeeze a singleton 4th dimension
        squeezed = work / 'squeezed.nii.gz'
        nib.Nifti1Image(np.asarray(img.dataobj)[..., 0], img.affine, img.header).to_filename(str(squeezed))
        nii = squeezed
    return nii


# ------------------------------------------------------------------ step 2: skull strip
def skullstrip(raw: Path, work: Path, device: str = 'cpu') -> Path:
    import importlib.util
    if importlib.util.find_spec('HD_BET') is None:
        raise PipelineError('INTERNAL', 'HD-BET is not installed on the server')
    out = work / 'brain.nii.gz'
    # Same as the `hd-bet` console script, run through this interpreter so no launcher .exe or PATH entry is needed.
    launcher = "import sys; from HD_BET.entry_point import main; sys.argv[0] = 'hd-bet'; main()"
    r = subprocess.run([sys.executable, '-c', launcher, '-i', str(raw), '-o', str(out), '-device', device,
                        '--save_bet_mask', '--no_bet_image', '--disable_tta'], capture_output=True, text=True)
    mask = work / 'brain_bet.nii.gz'
    if not mask.exists():
        found = sorted(work.glob('*_bet.nii.gz'))
        if not found:
            raise PipelineError('INTERNAL', f'HD-BET produced no mask (exit {r.returncode})')
        mask = found[0]
    return mask


# ------------------------------------------------------------------ steps 3–10
def register_and_normalise(raw: Path, mask_path: Path | None, cache_dir: Path, progress: Progress,
                           timings: dict, mask_override: Path | None = None) -> Preprocessed:
    """Steps 3–10. `mask_override` replaces the HD-BET mask (tests only: skip_skullstrip)."""
    import ants

    t_path, m_path = template_paths(cache_dir)
    t0 = time.perf_counter()
    img = ants.image_read(str(raw)).clone('float')
    mask = ants.image_read(str(mask_override or mask_path))
    mask = ants.resample_image_to_target(mask, img, interp_type='nearestNeighbor')
    brain_cm3 = float(mask.sum() * np.prod(img.spacing) / 1000)
    if brain_cm3 < MIN_BRAIN_CM3:
        raise PipelineError('QC_FAILED', f'brain mask volume {brain_cm3:.0f} cm³ < {MIN_BRAIN_CM3} cm³')

    progress('bias', 0.40)
    n4 = ants.n4_bias_field_correction(img, mask=mask, shrink_factor=PREPROC_SPEC['bias']['shrink_factor'])
    timings['bias'] = round(time.perf_counter() - t0, 2)

    progress('register', 0.55)
    t1 = time.perf_counter()
    tmpl = ants.image_read(str(t_path))
    tmask = ants.image_read(str(m_path))
    tm = tmask.numpy()
    lo, hi = crop_box(tm)
    check_crop(lo, hi)
    fixed, moving = tmpl * tmask, n4 * mask

    def attempt(kind: str):
        reg = ants.registration(fixed=fixed, moving=moving, type_of_transform=kind)
        wm = ants.apply_transforms(fixed=tmpl, moving=mask, transformlist=reg['fwdtransforms'],
                                   interpolator='nearestNeighbor')
        return reg, wm, dice(_crop(wm.numpy(), lo, hi), _crop(tm, lo, hi))

    reg, wmask, d = attempt(PREPROC_SPEC['register']['primary'])
    used = PREPROC_SPEC['register']['primary']
    if d < MIN_DICE:
        reg2, wmask2, d2 = attempt(PREPROC_SPEC['register']['fallback'])
        if d2 > d:
            reg, wmask, d, used = reg2, wmask2, d2, PREPROC_SPEC['register']['fallback']
    if d < MIN_DICE:
        raise PipelineError('QC_FAILED', f'registration to MNI failed QC (Dice {d:.3f} < {MIN_DICE})')
    warped = ants.apply_transforms(fixed=tmpl, moving=n4, transformlist=reg['fwdtransforms'], interpolator='linear')
    timings['register'] = round(time.perf_counter() - t1, 2)

    progress('normalise', 0.80)
    v = _crop(warped.numpy(), lo, hi).astype(np.float32)
    m = _crop(wmask.numpy(), lo, hi) > 0.5
    x = normalise(v, m)
    qc = {'brain_cm3': round(brain_cm3, 1), 'dice_mni': round(d, 4), 'registration': used, 'passed': True}
    return Preprocessed(x, qc, timings)


def normalise(v: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Steps 9–10: masked z-score, clip ±5, zero outside the mask, 2 mm block mean, float16 round-trip."""
    vals = v[m]
    z = (np.clip((v - vals.mean()) / (vals.std() + 1e-6), -5, 5) * m).astype(np.float32)
    return z.reshape(80, 2, 96, 2, 80, 2).mean(axis=(1, 3, 5)).astype(np.float16).astype(np.float32)


def run(src: Path, work: Path, cache_dir: Path, progress: Progress, device: str = 'cpu',
        skip_skullstrip: bool = False) -> Preprocessed:
    """Full pipeline. The caller owns `work` and must delete it (spec §6.14)."""
    timings: dict[str, float] = {}
    progress('convert', 0.02)
    t0 = time.perf_counter()
    raw = to_nifti(src, work)
    timings['convert'] = round(time.perf_counter() - t0, 2)

    progress('skullstrip', 0.10)
    t1 = time.perf_counter()
    if skip_skullstrip:
        _, m_path = template_paths(cache_dir)
        out = register_and_normalise(raw, None, cache_dir, progress, timings, mask_override=m_path)
    else:
        mask = skullstrip(raw, work, device)
        timings['skullstrip'] = round(time.perf_counter() - t1, 2)
        out = register_and_normalise(raw, mask, cache_dir, progress, timings)
    return out
