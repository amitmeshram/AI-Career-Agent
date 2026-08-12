from pathlib import Path
import argparse
import contextlib
import io
import sys

sys.dont_write_bytecode = True

from build_cv_optimization_draft import build_draft
from generate_cv_optimization_report import build_optimization_input
from generate_executive_cv_optimization_report_docx import build_docx


def generate_executive_report_from_evaluation(
    report_path: str,
    cv_path: str,
    output_path: str | None = None,
    force: bool = False,
):
    report = Path(report_path)
    cv = Path(cv_path)

    if not report.exists():
        raise FileNotFoundError(f"Evaluation report not found: {report}")

    if not cv.exists():
        raise FileNotFoundError(f"CV not found: {cv}")

    report_stem = report.stem
    optimization_input_path = build_optimization_input(
        report_path=str(report),
        cv_path=str(cv),
        output_dir=f"data/cv_optimization/inputs/{report_stem}",
    )

    optimization_draft_target = (
        Path("data/cv_optimization/drafts")
        / f"{report_stem}-optimization-draft.json"
    )

    with contextlib.redirect_stdout(io.StringIO()):
        optimization_draft_path = build_draft(
            str(optimization_input_path),
            output_path=optimization_draft_target,
        )

    if force:
        # The underlying generators overwrite deterministic outputs. This flag is
        # accepted for pipeline compatibility and documents intentional overwrite.
        pass

    executive_docx_target = Path(output_path) if output_path else None

    with contextlib.redirect_stdout(io.StringIO()):
        executive_docx_path = build_docx(
            str(optimization_draft_path),
            output_path=executive_docx_target,
        )

    return {
        "optimization_input_path": optimization_input_path,
        "optimization_draft_path": optimization_draft_path,
        "executive_docx_path": executive_docx_path,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate an Executive CV Optimization DOCX from a Phase 1 evaluation report."
    )
    parser.add_argument("--report", required=True, help="Path to Phase 1 evaluation report markdown file.")
    parser.add_argument("--cv", required=True, help="Path to current cv.md file.")
    parser.add_argument(
        "--output",
        help="Optional output DOCX path. Defaults to data/cv_optimization/reports/<company>-<role>-executive-report.docx.",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate deterministic outputs if they already exist.")

    args = parser.parse_args()

    paths = generate_executive_report_from_evaluation(
        report_path=args.report,
        cv_path=args.cv,
        output_path=args.output,
        force=args.force,
    )

    print()
    print(f"Optimization input path: {paths['optimization_input_path']}")
    print(f"Optimization draft path: {paths['optimization_draft_path']}")
    print(f"Executive DOCX path: {paths['executive_docx_path']}")


if __name__ == "__main__":
    main()
