"""Locate the raw PPMI data directory.

Raw PPMI data lives outside the repository. Its location comes from the
``PPMI_DATA_ROOT`` environment variable or a local, Git-ignored ``.env`` file,
and the directory is only ever read.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

ENV_VAR = "PPMI_DATA_ROOT"
DISABLE_DOTENV_VAR = "COPATH_DISABLE_DOTENV"

COMPONENT_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = COMPONENT_DIR.parents[1]
DEFAULT_DOTENV_PATHS = (COMPONENT_DIR / ".env", REPO_DIR / ".env")


class DataRootError(RuntimeError):
    """The raw-data directory is not configured or does not exist."""


def resolve_data_root(
    explicit: str | os.PathLike | None = None,
    env: Mapping[str, str] | None = None,
    dotenv_paths: tuple[Path, ...] | None = None,
) -> Path:
    """Return the raw-data directory.

    Precedence: ``explicit`` argument, then the ``PPMI_DATA_ROOT`` environment
    variable, then the first ``.env`` file that defines it. ``.env`` files are
    not consulted when ``COPATH_DISABLE_DOTENV`` is set.
    """
    env = os.environ if env is None else env
    value = str(explicit) if explicit else env.get(ENV_VAR, "")
    if not value and not env.get(DISABLE_DOTENV_VAR):
        from dotenv import dotenv_values

        for path in DEFAULT_DOTENV_PATHS if dotenv_paths is None else dotenv_paths:
            if Path(path).is_file():
                value = dotenv_values(path).get(ENV_VAR) or ""
                if value:
                    break
    value = value.strip().strip('"').strip("'")
    if not value or value.startswith("<"):
        raise DataRootError(
            f"{ENV_VAR} is not set. Define it in your environment or in a local .env file "
            "(see .env.example), or pass --data-root."
        )
    root = Path(value).expanduser()
    if not root.is_dir():
        raise DataRootError(f"The directory given by {ENV_VAR} does not exist or is not a directory.")
    return root
