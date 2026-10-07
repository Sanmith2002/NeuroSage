"""Loads the trained bundles once and keeps them in memory.

The bundles are used exactly as exported by Stage 4 / S4c: nothing is refit or re-thresholded.
`model_defs.py` (shipped next to the bundles) must be imported before unpickling, because the
NACC bundle pickles `model_defs.Platt` and the ADNI bundles need the torch net classes.
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib

from .config import Settings

log = logging.getLogger('ad-service.registry')

NACC_FILES = {'rf': 'nacc_multilabel_best.joblib', 'xgb': 'nacc_multilabel_xgb.joblib'}
ADNI_FILES = {'ad_clin': 'adni_ad_clin_best.joblib', 'ad_bio': 'adni_ad_bio_best.joblib',
              'ad_bio_fusion': 'adni_ad_bio_fusion.joblib'}


@dataclass
class Registry:
    settings: Settings
    model_defs: Any = None
    nacc: dict[str, dict] = field(default_factory=dict)        # 'rf' / 'xgb' → bundle
    adni: dict[str, dict] = field(default_factory=dict)        # 'ad_clin' / 'ad_bio' / 'ad_bio_fusion' → bundle
    nets: dict[str, list] = field(default_factory=dict)        # adni key → one eval-mode torch net per fold
    feature_stats: dict | None = None
    ood: dict | None = None
    model_card: dict | None = None
    load_times_s: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ------------------------------------------------------------------ loading
    @property
    def models_dir(self) -> Path:
        return self.settings.models_dir

    def _import_model_defs(self) -> None:
        if self.model_defs is not None:
            return
        if not (self.models_dir / 'model_defs.py').exists():
            raise FileNotFoundError(f'model_defs.py not found in {self.models_dir}')
        if str(self.models_dir) not in sys.path:
            sys.path.insert(0, str(self.models_dir))
        self.model_defs = importlib.import_module('model_defs')

    def _timed_load(self, key: str, path: Path) -> Any:
        t0 = time.perf_counter()
        obj = joblib.load(path)
        self.load_times_s[key] = round(time.perf_counter() - t0, 2)
        log.info('loaded %s in %.1fs', path.name, self.load_times_s[key])
        return obj

    def available_nacc(self) -> list[str]:
        return [k for k, f in NACC_FILES.items() if (self.models_dir / f).exists()]

    def active_nacc(self) -> str:
        """NACC_MODEL=auto prefers the light XGBoost bundle when it exists (spec §5.5)."""
        avail = self.available_nacc()
        choice = self.settings.nacc_model
        if choice == 'auto':
            return 'xgb' if 'xgb' in avail else 'rf'
        return choice

    def load(self) -> None:
        self._import_model_defs()
        active = self.active_nacc()
        if active not in self.available_nacc():
            raise FileNotFoundError(f'NACC bundle {NACC_FILES[active]} not found in {self.models_dir}')
        self.get_nacc(active)

        for name, attr in [('feature_stats.json', 'feature_stats'), ('model_card.json', 'model_card')]:
            p = self.models_dir / name
            if p.exists():
                setattr(self, attr, json.loads(p.read_text(encoding='utf-8')))
        if (self.models_dir / 'ood_nacc.joblib').exists():
            self.ood = self._timed_load('ood', self.models_dir / 'ood_nacc.joblib')

        if self.settings.load_mri:
            self.load_adni()

    def get_nacc(self, key: str) -> dict:
        """Returns a NACC bundle, loading it on first use (the RF pickle is ~450 MB)."""
        if key not in NACC_FILES:
            raise KeyError(key)
        with self._lock:
            if key not in self.nacc:
                path = self.models_dir / NACC_FILES[key]
                if not path.exists():
                    raise FileNotFoundError(f'{path.name} not available')
                self._import_model_defs()
                bundle = self._timed_load(f'nacc_{key}', path)
                # Runtime-only: one-row requests are ~2× faster single-threaded. Predictions are unchanged.
                for fold in bundle['folds']:
                    for est in fold:
                        m = est[-1] if hasattr(est, 'steps') else est
                        if hasattr(m, 'n_jobs'):
                            m.n_jobs = 1
                self.nacc[key] = bundle
            return self.nacc[key]

    def load_adni(self) -> None:
        self._import_model_defs()
        for key, fname in ADNI_FILES.items():
            if key == 'ad_bio_fusion' and not self.settings.load_bio_fusion:
                continue
            path = self.models_dir / fname
            if not path.exists():
                continue
            bundle = self._timed_load(key, path)
            self.adni[key] = bundle
            if bundle['kind'] != 'tabular':
                self.nets[key] = self._build_nets(bundle)

    def _build_nets(self, bundle: dict) -> list:
        """Spec §6.12: build the torch nets once at startup, not per request as predict_adni does."""
        nets = []
        for f in bundle['folds']:
            net = self.model_defs.build_net(bundle['kind'], bundle['arch'], len(bundle['tab_features']))
            net.load_state_dict(f['state'])
            net.eval()
            for p in net.parameters():
                p.requires_grad_(False)
            nets.append(net)
        return nets

    # ------------------------------------------------------------------ status
    def summary(self) -> dict:
        return {
            'nacc_available': self.available_nacc(),
            'nacc_loaded': sorted(self.nacc),
            'nacc_active': self.active_nacc(),
            'adni_loaded': sorted(self.adni),
            'feature_stats': self.feature_stats is not None,
            'ood': self.ood is not None,
            'model_card': self.model_card is not None,
            'load_times_s': self.load_times_s,
        }
