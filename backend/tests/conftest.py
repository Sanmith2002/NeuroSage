import os
import sys
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE))
os.environ.setdefault('API_KEY', '')
PRIVATE = SERVICE / 'tests' / 'private'


def models_present() -> bool:
    from app.config import default_models_dir
    d = default_models_dir()
    return (d / 'model_defs.py').exists() and any(
        (d / f).exists() for f in ['nacc_multilabel_best.joblib', 'nacc_multilabel_xgb.joblib'])


@pytest.fixture(scope='session')
def client():
    if not models_present():
        pytest.skip('model files not present in the repo-root models/ folder')
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert c.app.state.load_error is None, c.app.state.load_error
        yield c


@pytest.fixture(scope='session')
def registry(client):
    return client.app.state.registry
