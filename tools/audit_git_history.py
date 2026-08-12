from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath


MAX_BLOB_BYTES = 5 * 1024 * 1024

ALLOWED_PRIVATE_PATHS = {
    ".env.example",
    "apps/gmail-agent/.env.example",
    "apps/gmail-agent/credentials.example.json",
    "config/profile.example.yml",
    "examples/article-digest-example.md",
    "examples/cv-example.md",
    "examples/dual-track-engineer-instructor/profile.yml",
    "templates/portals.example.yml",
}

ALLOWED_PRIVATE_PREFIXES = (
    "examples/",
    "apps/gmail-agent/test_",
)

PRIVATE_EXACT_PATHS = {
    ".env",
    "article-digest.md",
    "config/master_profile.yml",
    "config/profile.yml",
    "credentials.json",
    "cv.md",
    "modes/_profile.md",
    "portals.yml",
    "token.json",
}

PRIVATE_PREFIXES = (
    "data/gmail-agent/",
    "apps/gmail-agent/logs/",
    "batch/tracker-additions/",
    "data/cv_optimization/",
    "data/profile_reviews/",
    "data/resume_objects/",
    "data/tailored_cvs/",
    "data/tailoring_intelligence/",
    "jds/",
    "output/",
    "reports/",
)

PRIVATE_BASENAME_PATTERNS = (
    re.compile(r"^cv(?:\s*-\s*old|\s*-\s*ver-\d+|_backup).*", re.IGNORECASE),
    re.compile(r"^profile_backup.*\.ya?ml$", re.IGNORECASE),
    re.compile(r"^credentials\.json$", re.IGNORECASE),
    re.compile(r"^token\.json$", re.IGNORECASE),
)

SECRET_PATTERNS = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----")),
    (
        "oauth_refresh_token",
        re.compile(r'"refresh_token"\s*:\s*"[^"]{20,}"', re.IGNORECASE),
    ),
    (
        "client_secret",
        re.compile(r'"client_secret"\s*:\s*"(?!(?:your-|example|placeholder))[^"]{12,}"', re.IGNORECASE),
    ),
    (
        "oauth_url_token",
        re.compile(r"[?&](?:auth_token|access_token|refresh_token|emailtoken|usertoken)=[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    ),
)

ENV_SECRET_ASSIGNMENT = (
    "env_secret_assignment",
    re.compile(
        r"(?im)^\s*(?:[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*)\s*=\s*(?!$|your_|change-me|placeholder|example|xxx)[^\s#]{12,}"
    ),
)

SECRET_CONTEXT_LINE = re.compile(r"(?i)(api[_-]?key|secret|token|password|authorization|bearer)")
HIGH_ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9_.+=/-]{32,}")

ENV_LIKE_FILENAMES = {
    ".env",
    ".env.example",
    "env.example",
}

LOCK_OR_CHECKSUM_PATHS = (
    "flake.lock",
    "go.sum",
    "package-lock.json",
)

SECRET_CONTEXT_SKIP_SUFFIXES = (
    ".lock",
    ".sum",
)

SECRET_CONTEXT_SKIP_PATHS = {
    "CHANGELOG.md",
    "README.cn.md",
    "README.es.md",
    "README.ja.md",
    "README.ko-KR.md",
    "README.md",
    "README.pt-BR.md",
    "README.ru.md",
    "README.zh-TW.md",
}


def is_env_like_path(path: str) -> bool:
    return PurePosixPath(path).name in ENV_LIKE_FILENAMES


def should_skip_context_entropy(path: str) -> bool:
    path = normalize_path(path)
    if path in SECRET_CONTEXT_SKIP_PATHS:
        return True
    if path.endswith(SECRET_CONTEXT_SKIP_SUFFIXES):
        return True
    return any(path.endswith(item) for item in LOCK_OR_CHECKSUM_PATHS)


def has_contextual_high_entropy_secret(text: str, path: str) -> bool:
    if should_skip_context_entropy(path):
        return False
    for line in text.splitlines():
        if not SECRET_CONTEXT_LINE.search(line):
            continue
        for candidate in HIGH_ENTROPY_CANDIDATE.findall(line):
            if 32 <= len(candidate) <= 160 and shannon_entropy(candidate) >= 4.4:
                return True
    return False


LEGACY_PRIVATE_PATHS = {
    "current_run_reports.json",
}

LEGACY_PRIVATE_PREFIXES: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    kind: str
    rule: str
    object: str
    path: str


def run_git(args: list[str], *, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    return result.stdout


def normalize_path(path: str) -> str:
    value = path.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def is_allowed_private_path(path: str) -> bool:
    path = normalize_path(path)
    return path in ALLOWED_PRIVATE_PATHS or any(path.startswith(prefix) for prefix in ALLOWED_PRIVATE_PREFIXES)


def sensitive_path_rule(path: str) -> str | None:
    path = normalize_path(path)
    if is_allowed_private_path(path):
        return None

    if path in LEGACY_PRIVATE_PATHS:
        return "legacy_private_path"

    if path in PRIVATE_EXACT_PATHS:
        return "private_path_exact"

    if any(path.startswith(prefix) for prefix in LEGACY_PRIVATE_PREFIXES):
        return "legacy_private_path_prefix"

    if any(path.startswith(prefix) for prefix in PRIVATE_PREFIXES):
        return "private_path_prefix"

    basename = PurePosixPath(path).name
    if any(pattern.search(basename) for pattern in PRIVATE_BASENAME_PATTERNS):
        return "private_path_basename"

    return None


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {character: value.count(character) for character in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def content_rules(text: str, path: str) -> set[str]:
    if is_allowed_private_path(path):
        return set()

    matches = {name for name, pattern in SECRET_PATTERNS if pattern.search(text)}
    if is_env_like_path(path) and ENV_SECRET_ASSIGNMENT[1].search(text):
        matches.add(ENV_SECRET_ASSIGNMENT[0])

    if has_contextual_high_entropy_secret(text, path):
        matches.add("high_entropy_string")
    return matches


def iter_history_objects() -> dict[str, set[str]]:
    raw = run_git(["rev-list", "--objects", "--all"])
    objects: dict[str, set[str]] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        object_id = parts[0]
        path = normalize_path(parts[1]) if len(parts) > 1 else ""
        objects.setdefault(object_id, set())
        if path:
            objects[object_id].add(path)
    return objects


def object_metadata(object_ids: list[str]) -> dict[str, tuple[str, int]]:
    if not object_ids:
        return {}
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        check=True,
        input="\n".join(object_ids) + "\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    metadata = {}
    for line in result.stdout.splitlines():
        object_id, object_kind, object_size = line.split(" ", 2)
        metadata[object_id] = (object_kind, int(object_size))
    return metadata


def blob_texts(metadata: dict[str, tuple[str, int]]) -> dict[str, str]:
    texts = {}
    wanted = [
        object_id
        for object_id, (object_kind, object_size) in metadata.items()
        if object_kind == "blob" and object_size <= MAX_BLOB_BYTES
    ]
    if not wanted:
        return texts

    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    for object_id in wanted:
        process.stdin.write((object_id + "\n").encode("ascii"))
        process.stdin.flush()
        header = process.stdout.readline().decode("ascii", errors="replace").strip()
        if not header:
            continue
        parts = header.split(" ")
        if len(parts) != 3 or parts[1] != "blob":
            continue
        size = int(parts[2])
        data = process.stdout.read(size)
        process.stdout.read(1)
        if b"\x00" in data[:4096]:
            continue
        texts[object_id] = data.decode("utf-8", errors="ignore")

    process.stdin.close()
    process.stdout.close()
    process.wait(timeout=30)
    return texts


def audit_history() -> list[Finding]:
    findings: set[Finding] = set()
    objects = iter_history_objects()
    metadata = object_metadata(list(objects))
    texts = blob_texts(metadata)
    for object_id, paths in objects.items():
        for path in paths:
            rule = sensitive_path_rule(path)
            if rule:
                findings.add(Finding("path", rule, object_id, path))

        text = texts.get(object_id)
        if text is None:
            continue
        for path in paths or {""}:
            if is_allowed_private_path(path):
                continue
            for rule in content_rules(text, path):
                findings.add(Finding("content", rule, object_id, path))

    return sorted(findings, key=lambda item: (item.kind, item.path, item.rule, item.object))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Git history for private files and common secret patterns without printing secret values."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    run_git(["rev-parse", "--show-toplevel"])
    findings = audit_history()

    if args.json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    else:
        print("Git history privacy audit")
        print("=========================")
        print(f"Findings: {len(findings)}")
        for finding in findings:
            print(
                f"- {finding.kind}: {finding.rule} | "
                f"object={finding.object[:12]} | path={finding.path or '<unknown>'}"
            )

        if findings:
            print()
            print("Do not publish this repository history until these findings are reviewed and sanitized.")
        else:
            print("No private paths or common secret patterns were detected in Git history.")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
