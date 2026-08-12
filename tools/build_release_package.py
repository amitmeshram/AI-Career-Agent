from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_FILES = {
    ".coderabbit.yaml",
    ".env.example",
    ".gitignore",
    ".release-please-manifest.json",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CONTRIBUTORS.md",
    "DATA_CONTRACT.md",
    "GEMINI.md",
    "GOVERNANCE.md",
    "LEGAL_DISCLAIMER.md",
    "LICENSE",
    "README.cn.md",
    "README.es.md",
    "README.ja.md",
    "README.ko-KR.md",
    "README.md",
    "README.pt-BR.md",
    "README.ru.md",
    "README.zh-TW.md",
    "RUNBOOK.md",
    "SECURITY.md",
    "SETUP.md",
    "SUPPORT.md",
    "VERSION",
    "flake.lock",
    "flake.nix",
    "package.json",
    "renovate.json",
    "requirements.txt",
    "run.py",
    "setup_macos.sh",
    "setup_windows.ps1",
}

ROOT_SUFFIXES = (".mjs",)

ALLOW_PREFIXES = (
    ".claude-plugin/",
    ".claude/skills/",
    ".gemini/commands/",
    ".github/",
    ".opencode/commands/",
    "apps/gmail-agent/",
    "batch/",
    "config/",
    "dashboard/",
    "data/",
    "docs/",
    "examples/",
    "fonts/",
    "interview-prep/",
    "jds/",
    "modes/",
    "templates/",
    "tools/",
)

DENY_EXACT = {
    ".env",
    ".envrc",
    ".update-dismissed",
    ".update-lock",
    "article-digest.md",
    "apps/gmail-agent/.env",
    "apps/gmail-agent/credentials.json",
    "apps/gmail-agent/token.json",
    "batch/batch-input.tsv",
    "batch/batch-state.tsv",
    "config/master_profile.yml",
    "config/profile.yml",
    "credentials.json",
    "cv.md",
    "data/applications.md",
    "data/follow-ups.md",
    "data/pipeline.md",
    "data/scan-history.tsv",
    "modes/_profile.md",
    "package-lock.json",
    "portals.yml",
    "token.json",
}

DENY_PREFIXES = (
    ".git/",
    ".tmp",
    ".venv/",
    "apps/gmail-agent/.venv/",
    "apps/gmail-agent/logs/",
    "backup/",
    "batch/logs/",
    "batch/tracker-additions/",
    "data/",
    "data/cv_optimization/",
    "data/profile_reviews/",
    "data/resume_objects/",
    "data/tailored_cvs/",
    "data/tailoring_intelligence/",
    "dist/",
    "final run/",
    "jds/",
    "node_modules/",
    "output/",
    "reports/",
    "reports_before_",
    "reports_duplicates/",
    "reports_old/",
    "reports_old_spanish/",
)

DENY_SUFFIXES = (
    ".pyc",
    ".mov",
    ".mp4",
)

ALLOWED_EMPTY_MARKERS = {
    "batch/logs/.gitkeep",
    "data/.gitkeep",
    "data/gmail-agent/.gitkeep",
    "jds/.gitkeep",
    "reports/.gitkeep",
    "reports/daily/.gitkeep",
}

SOURCE_ONLY_DENY_EXACT = {
    "interview-prep/story-bank.md",
}

STORY_BANK_TEMPLATE = """# Story Bank - Master STAR+R Stories

This file accumulates your best interview stories over time. Each evaluation
can add new STAR+R stories here.

## Stories

<!-- Stories will be added here as you evaluate offers. -->
"""


def run_git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def normalize(path: Path | str) -> str:
    value = str(path).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def is_release_allowed(path: str) -> bool:
    path = normalize(path)
    name = PurePosixPath(path).name
    parts = PurePosixPath(path).parts

    if path in ALLOWED_EMPTY_MARKERS:
        return True
    if "__pycache__" in parts:
        return False
    if path in DENY_EXACT:
        return False
    if any(path.startswith(prefix) for prefix in DENY_PREFIXES):
        return False
    if path.endswith(DENY_SUFFIXES):
        return False
    if ".pyc" in name:
        return False
    if name.startswith("~$"):
        return False

    if path in ROOT_FILES:
        return True
    if "/" not in path and path.endswith(ROOT_SUFFIXES):
        return True
    return any(path.startswith(prefix) for prefix in ALLOW_PREFIXES)


def git_tracked_files(root: Path) -> set[str]:
    raw = run_git(["ls-files", "-z"], cwd=root)
    return {normalize(item) for item in raw.split("\0") if item}


def release_files(root: Path) -> list[str]:
    candidates = git_tracked_files(root)

    # Include this release tooling during local pre-commit test runs.
    for extra in (
        "setup_macos.sh",
        "setup_windows.ps1",
        "tools/audit_git_history.py",
        "tools/build_release_package.py",
    ):
        if (root / extra).exists():
            candidates.add(extra)

    return sorted(
        path
        for path in candidates
        if path not in SOURCE_ONLY_DENY_EXACT and is_release_allowed(path) and (root / path).is_file()
    )


def transform_text(path: str, text: str) -> str:
    return text


def copy_release_file(root: Path, output_dir: Path, path: str) -> None:
    source = root / path
    target = output_dir / path
    target.parent.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() in {".md", ".mjs", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".sh", ".ps1", ".html", ".tex", ".cff", ".mod", ".sum"} or source.name in {
        ".env.example",
        ".gitignore",
        "LICENSE",
        "VERSION",
    }:
        text = source.read_text(encoding="utf-8", errors="ignore")
        target.write_text(transform_text(path, text), encoding="utf-8")
    else:
        shutil.copy2(source, target)


def write_release_defaults(output_dir: Path) -> None:
    story_bank = output_dir / "interview-prep" / "story-bank.md"
    story_bank.parent.mkdir(parents=True, exist_ok=True)
    story_bank.write_text(STORY_BANK_TEMPLATE, encoding="utf-8")


def ensure_within_root(root: Path, target: Path) -> None:
    resolved = target.resolve()
    if resolved == root:
        raise ValueError("Output directory cannot be the repository root.")
    if root not in resolved.parents:
        raise ValueError(f"Output directory must stay inside the repository: {resolved}")


def remove_tree(path: Path) -> None:
    def make_writable(function, target, _exc_info):
        Path(target).chmod(stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onerror=make_writable)


def validate_package(output_dir: Path) -> list[str]:
    violations = []
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = normalize(path.relative_to(output_dir))
        if not is_release_allowed(relative):
            violations.append(relative)
    return sorted(violations)


def zip_directory(output_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir).as_posix())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_name(root: Path) -> str:
    version_file = root / "VERSION"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
    else:
        version = json.loads((root / "package.json").read_text(encoding="utf-8"))["version"]
    return f"career-ops-{version or 'release'}"


def build_release(root: Path, output_dir: Path, zip_path: Path | None, clean: bool) -> dict[str, object]:
    ensure_within_root(root, output_dir)
    if zip_path:
        ensure_within_root(root, zip_path)

    if output_dir.exists():
        if not clean:
            raise FileExistsError(f"Output directory already exists: {output_dir}")
        remove_tree(output_dir)
    output_dir.mkdir(parents=True)

    files = release_files(root)
    for path in files:
        copy_release_file(root, output_dir, path)
    write_release_defaults(output_dir)

    violations = validate_package(output_dir)
    if violations:
        raise RuntimeError("Denied files reached release package: " + ", ".join(violations))

    summary: dict[str, object] = {
        "output_dir": str(output_dir),
        "file_count": sum(1 for path in output_dir.rglob("*") if path.is_file()),
        "zip": None,
        "sha256": None,
    }

    if zip_path:
        if zip_path.exists():
            zip_path.unlink()
        zip_directory(output_dir, zip_path)
        checksum = sha256_file(zip_path)
        checksum_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
        checksum_path.write_text(f"{checksum}  {zip_path.name}\n", encoding="utf-8")
        summary.update(
            {
                "zip": str(zip_path),
                "sha256": checksum,
                "sha256_file": str(checksum_path),
            }
        )

    return summary


def main() -> int:
    root = repo_root()
    default_name = package_name(root)
    parser = argparse.ArgumentParser(
        description="Build a reproducible public release package from approved files only."
    )
    parser.add_argument(
        "--output-dir",
        default="final run",
        help="Staging folder to rebuild. Defaults to 'final run'.",
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        default=f"dist/{default_name}.zip",
        help="Zip file to create. Use --no-zip to skip.",
    )
    parser.add_argument("--no-zip", action="store_true", help="Build the folder only.")
    parser.add_argument("--no-clean", action="store_true", help="Fail if output dir exists instead of replacing it.")
    args = parser.parse_args()

    output_dir = (root / args.output_dir).resolve()
    zip_path = None if args.no_zip else (root / args.zip_path).resolve()

    summary = build_release(
        root=root,
        output_dir=output_dir,
        zip_path=zip_path,
        clean=not args.no_clean,
    )

    print("Release package built")
    print("=====================")
    print(f"Output: {summary['output_dir']}")
    print(f"Files: {summary['file_count']}")
    if summary["zip"]:
        print(f"Zip: {summary['zip']}")
        print(f"SHA256: {summary['sha256']}")
        print(f"Checksum file: {summary['sha256_file']}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"release package failed: {exc}", file=sys.stderr)
        sys.exit(1)
