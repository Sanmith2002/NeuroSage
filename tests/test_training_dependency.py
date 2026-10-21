import sys

import pytest


def test_feature_005_runtime_dependency_is_the_approved_python_311_sklearn_pin():
    import importlib.metadata
    import tomllib
    from pathlib import Path

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert sys.version_info >= (3, 11)
    assert "scikit-learn==1.7.1" in project["project"]["dependencies"]
    assert importlib.metadata.version("scikit-learn") == "1.7.1"
    from sklearn.linear_model import LogisticRegression

    assert LogisticRegression.__name__ == "LogisticRegression"
