"""Command line of the frozen inference package::

    python -m copath.inference --input <record.json|record.csv> [--output <result.json>]
    python -m copath.inference --make-synthetic-example <file> [--missing-modalities A,B] [--cohort PD]
    python -m copath.inference --write-contracts --from-bundle         (writes docs/*.json, docs/input_features_v1.md)
    python -m copath.inference --check-contracts --from-bundle         (READ-ONLY: compares the committed input contract with the bundle)

The output goes to the console, or only to the --output path; a path inside the git working tree that is not git-ignored is refused.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import contracts
from .bundle import BundleIntegrityError, load_bundle
from .explanations import AdditivityError, SpecError
from .predict import predict_batch, predict_record
from .schema import InputValidationError
from .synthetic import make_synthetic_record


class OutputPathError(RuntimeError):
    """The output path would put participant-level results into a tracked part of the repository."""


def _repo_root(path: Path) -> Path | None:
    for folder in [path.resolve(), *path.resolve().parents]:
        if (folder / ".git").exists():
            return folder
    return None


def check_output_path(path: Path) -> Path:
    """Refuse a path inside a git working tree unless git ignores it. Returns the resolved path."""
    target = Path(path).resolve()
    root = _repo_root(target.parent if not target.is_dir() else target)
    if root is None:
        return target
    ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--", str(target)], capture_output=True).returncode == 0
    if not ignored:
        raise OutputPathError("refused: the output path is inside the git working tree and is not git-ignored. Choose a path outside "
                              "the repository or a git-ignored folder; participant-level results must not end up in tracked files.")
    return target


def read_records(path: Path) -> tuple[list[dict], bool]:
    """Records of a JSON (object or list of objects) or CSV file, and whether the input was a single record."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        import pandas as pd

        table = pd.read_csv(path, dtype=str, keep_default_na=False)  # text stays text: every value is validated strictly
        return table.to_dict(orient="records"), len(table) == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data], True
    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        return data, False
    raise InputValidationError([], "the JSON input must be one object or a list of objects")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m copath.inference", description="Frozen-model inference (research proxy signals).")
    parser.add_argument("--input", help="JSON or CSV file with one record (or several)")
    parser.add_argument("--output", help="write the JSON result here instead of printing it")
    parser.add_argument("--make-synthetic-example", metavar="FILE", help="write one fully synthetic record (SYNTHETIC_DEMO_001). The record uses deterministic values derived from feature names "
                        "solely to exercise the inference pipeline. Many values may be outside realistic clinical ranges. Its probabilities and "
                        "feature contributions have no clinical or scientific interpretation and are for engineering smoke testing only.")
    parser.add_argument("--missing-modalities", default="", help="comma-separated modalities left out of the synthetic record")
    parser.add_argument("--cohort", default=None, help="optional cohort for the synthetic record")
    parser.add_argument("--write-contracts", action="store_true", help="write docs/input_schema_v1.json, docs/input_features_v1.md, docs/output_schema_v1.json "
                        "(requires --from-bundle: the v1 input contract is the raw feature union of the frozen bundle)")
    parser.add_argument("--check-contracts", action="store_true", help="READ-ONLY: compare the committed input contract (schema and feature table) with the "
                        "frozen bundle and exit non-zero on any mismatch (requires --from-bundle)")
    parser.add_argument("--from-bundle", action="store_true", help="take the feature list from the verified frozen bundle")
    args = parser.parse_args(argv)
    try:
        if args.make_synthetic_example:
            features = {name: meta["modality"] for name, meta in contracts.read_contract().items()}
            record = make_synthetic_record(features, tuple(m for m in args.missing_modalities.split(",") if m), args.cohort)
            Path(args.make_synthetic_example).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
            print(f"wrote a fully synthetic record with {len(record) - 1 - bool(args.cohort)} features", file=sys.stderr)
            return 0
        if args.write_contracts or args.check_contracts:
            if not args.from_bundle:
                parser.error("--write-contracts and --check-contracts require --from-bundle: the v1 input contract is the raw "
                             "pre-pipeline feature union of the frozen bundle, not the modelling-tier configuration")
            loaded = load_bundle()  # verified first
            if args.check_contracts:
                problems = contracts.check_contracts(loaded)
                for line in problems:
                    print(f"CONTRACT MISMATCH: {line}", file=sys.stderr)
                print("the committed input contract matches the frozen bundle" + f" ({len(loaded.features)} features)" if not problems
                      else f"{len(problems)} contract problem(s)", file=sys.stderr)
                return 0 if not problems else 6
            for path in contracts.write_contracts(contracts.bundle_features(loaded)):
                print(f"wrote {path.name}", file=sys.stderr)
            return 0
        if not args.input:
            parser.error("--input is required")
        target = check_output_path(Path(args.output)) if args.output else None  # refuse BEFORE doing any work
        bundle = load_bundle()  # verifies the frozen bundle first; no fallback
        for line in bundle.warnings:
            print(f"WARNING: {line}", file=sys.stderr)
        print(f"bundle verified ({bundle.model_version}; training versions from {bundle.version_source})", file=sys.stderr)
        records, single = read_records(Path(args.input))
        result = predict_record(bundle, records[0]) if single else predict_batch(bundle, records)
        text = json.dumps(result, indent=2) + "\n"
        if target is not None:
            target.write_text(text, encoding="utf-8")
            print(f"result written to the --output path ({len(records)} record(s))", file=sys.stderr)
        else:
            print(text, end="")
        return 0
    except OutputPathError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except BundleIntegrityError as exc:
        print(f"BUNDLE INTEGRITY ERROR: {exc}", file=sys.stderr)
        return 3
    except InputValidationError as exc:
        print(f"INPUT VALIDATION ERROR: {exc}", file=sys.stderr)
        return 4
    except (AdditivityError, SpecError) as exc:
        print(f"EXPLANATION ERROR: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:  # noqa: BLE001 - never print a message that may quote data
        print(f"inference failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
