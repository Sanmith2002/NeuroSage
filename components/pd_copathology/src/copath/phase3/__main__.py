"""Phase 3 command line::

    python -m copath.phase3 cv [--label L ...] [--model M ...]
    python -m copath.phase3 select --stage preliminary
    python -m copath.phase3 robustness
    python -m copath.phase3 select --stage final
    python -m copath.phase3 extras
    python -m copath.phase3 explain
    ---- human review of reports/phase3 ----
    python -m copath.phase3 final --final        (needs configs/frozen/final_approval.yaml)
"""

from __future__ import annotations

import argparse
import sys

from ..data.provenance import error_record
from ..data.split import SplitError, TestSetAccessError
from ..features.leakage_guard import LeakageError
from ..targets.builders import CardError
from . import commands, final
from .core import ALL_MODELS, Phase3Error, PrivacyCheckError, load_context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m copath.phase3", description="Phase 3: training, selection and evaluation.")
    sub = parser.add_subparsers(dest="command", required=True)
    cv = sub.add_parser("cv", help="baselines and candidates, primary tier, nested CV (long)")
    cv.add_argument("--label", action="append", help="only this label (repeatable)")
    cv.add_argument("--model", action="append", choices=ALL_MODELS, help="only this model (repeatable)")
    select = sub.add_parser("select", help="model selection")
    select.add_argument("--stage", required=True, choices=["preliminary", "final"])
    sub.add_parser("robustness", help="strict tier, seeds and SHAP stability for the tie-set models")
    sub.add_parser("extras", help="ablation, sensitivity labels, medication-record check, calibration comparison")
    sub.add_parser("explain", help="SHAP reports for the selected models")
    last = sub.add_parser("final", help="single test-set evaluation; locked until a human approval file exists")
    last.add_argument("--final", action="store_true", help="required to run the final evaluation")
    last.add_argument("--force", action="store_true", help="run again although the lock file exists (needs --reason)")
    last.add_argument("--reason", default="", help="why a forced second run is needed (logged)")
    args = parser.parse_args(argv)
    try:
        if args.command == "final":
            final.cmd_final(final_flag=args.final, force=args.force, reason=args.reason)
            return 0
        ctx = load_context()
        if args.command == "cv":
            commands.cmd_cv(ctx, args.label, args.model)
        elif args.command == "select":
            (commands.cmd_select_preliminary if args.stage == "preliminary" else commands.cmd_select_final)(ctx)
        elif args.command == "robustness":
            commands.cmd_robustness(ctx)
        elif args.command == "extras":
            commands.cmd_extras(ctx)
        elif args.command == "explain":
            commands.cmd_explain(ctx)
        ctx.log(f"{args.command} finished. Aggregate reports: {ctx.paths.reports}")
        return 0
    except PrivacyCheckError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except final.FinalLockError as exc:
        print(f"LOCKED: {exc}", file=sys.stderr)
        return 5
    except (Phase3Error, TestSetAccessError, SplitError, LeakageError, CardError) as exc:
        print(f"Phase 3 stopped: {exc}", file=sys.stderr)  # messages written by this package; no data
        return 1
    except Exception as exc:  # noqa: BLE001 - never print a message that may quote data
        record = error_record("", "", args.command, exc)
        print(f"Phase 3 failed in '{args.command}': {record['exception_type']} at {record['location'] or 'unknown location'}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
