"""Phase 3 command line::

    python -m copath.phase3 cv [--label L ...] [--model M ...]
    python -m copath.phase3 missingness-audit   (pd_type_v1 only; needs `select --stage final` for the extra run)
    python -m copath.phase3 report-final        (read-only; after `final` has run)
    python -m copath.phase3 package-final-bundle [--verify]   (provenance metadata next to the frozen bundle; additive only)
    python -m copath.phase3 verify-explainer-spec             (development set only; prints aggregate scalars)
    python -m copath.phase3 reset-cv --confirm   (removes ONLY the cv outputs; refused once a final run or lock exists)
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
from . import commands, final, missingness, packaging, report_final, reset
from .core import ALL_MODELS, Phase3Error, PrivacyCheckError, load_context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m copath.phase3", description="Phase 3: training, selection and evaluation.")
    sub = parser.add_subparsers(dest="command", required=True)
    cv = sub.add_parser("cv", help="baselines and candidates, primary tier, nested CV (long)")
    cv.add_argument("--label", action="append", help="only this label (repeatable)")
    cv.add_argument("--model", action="append", choices=ALL_MODELS, help="only this model (repeatable)")
    wipe = sub.add_parser("reset-cv", help="remove ONLY the cv outputs (registry rows, oof files, cv reports) to restart cv")
    wipe.add_argument("--confirm", action="store_true", help="really remove them (without it nothing is removed)")
    pack = sub.add_parser("package-final-bundle", help="add provenance metadata next to the frozen final bundle (additive; no model is touched)")
    pack.add_argument("--verify", action="store_true", help="only recompute every hash and compare it with the manifest; writes nothing")
    sub.add_parser("verify-explainer-spec", help="compare the packaged explanation convention with shap on the DEVELOPMENT set (aggregate scalars)")
    sub.add_parser("report-final", help="READ-ONLY aggregate reports and figures from the predictions `final` saved")
    sub.add_parser("missingness-audit", help="pd_type_v1: availability of each feature in PD vs HC, and a low-gap-features run")
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
        if args.command == "package-final-bundle":
            if args.verify:
                problems = packaging.verify()
                for line in problems:
                    print(f"VERIFY FAILED: {line}", file=sys.stderr)
                print("bundle packaging verified" if not problems else f"{len(problems)} problem(s)")
                return 0 if not problems else 1
            packaging.cmd_package(log=lambda m: print(m, file=sys.stderr))
            return 0
        if args.command == "verify-explainer-spec":
            packaging.cmd_verify_explainer_spec(log=print)
            return 0
        if args.command == "reset-cv":
            reset.cmd_reset_cv(confirm=args.confirm, log=lambda m: print(m, file=sys.stderr))
            return 0
        ctx = load_context()
        if args.command == "cv":
            failed = commands.cmd_cv(ctx, args.label, args.model)
            if failed:
                print(f"Phase 3 cv finished with {len(failed)} FAILED run(s) (no metrics were written for them; see the log above): "
                      + ", ".join(failed), file=sys.stderr)
                return 4
        elif args.command == "select":
            (commands.cmd_select_preliminary if args.stage == "preliminary" else commands.cmd_select_final)(ctx)
        elif args.command == "report-final":
            report_final.cmd_report_final(ctx)
        elif args.command == "missingness-audit":
            missingness.cmd_missingness_audit(ctx)
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
