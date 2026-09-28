"""Git als Sicherheitsnetz: Basis-Commit je Task, Diff für Reviews, Commit oder Rollback."""
from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from config import PROTECTED_PREFIXES, REPO_ROOT

REVIEW_EXCLUDE = (
    "*package-lock.json", "*.lock", "web/drizzle/meta/*", "*next-env.d.ts",
    "*.png", "*.jpg", "*.jpeg", "*.ico", "*.webp", "*.woff*",
)


class GitError(RuntimeError):
    pass


def git(*args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout


def is_clean() -> bool:
    return git("status", "--porcelain").strip() == ""


def head() -> str:
    return git("rev-parse", "HEAD").strip()


def has_identity() -> bool:
    return bool(git("config", "user.email", check=False).strip())


def stage_all() -> None:
    git("add", "-A")


def changed_files(base: str) -> list[str]:
    stage_all()
    return [f for f in git("diff", "--cached", "--name-only", base).splitlines() if f.strip()]


def _excluded(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in REVIEW_EXCLUDE)


def diff_stat(base: str) -> str:
    stage_all()
    return git("diff", "--cached", "--stat", base).strip() or "(keine Änderungen)"


def diff_for_review(base: str, budget: int) -> str:
    """Diff seit Basis, ohne Lockfiles/Binärdateien, mit Zeichenbudget."""
    stage_all()
    parts = [f"# git diff --stat\n{diff_stat(base)}\n"]
    used = len(parts[0])
    skipped: list[str] = []
    for f in changed_files(base):
        if _excluded(f):
            skipped.append(f"{f} (ausgeblendet)")
            continue
        d = git("diff", "--cached", base, "--", f)
        if used + len(d) > budget:
            remaining = budget - used
            if remaining > 2000:
                parts.append(d[:remaining] + f"\n[... {f} gekürzt ...]\n")
                used = budget
            else:
                skipped.append(f"{f} (Budget erschöpft)")
            continue
        parts.append(d)
        used += len(d)
    if skipped:
        parts.append("# Nicht im Diff gezeigt:\n" + "\n".join(f"- {s}" for s in skipped))
    return "\n".join(parts)


def protected_changes(base: str) -> list[str]:
    return [f for f in changed_files(base) if f.startswith(PROTECTED_PREFIXES)]


def restore_paths(base: str, paths: list[str]) -> None:
    for f in paths:
        existed = subprocess.run(["git", "cat-file", "-e", f"{base}:{f}"], cwd=REPO_ROOT).returncode == 0
        if existed:
            git("restore", f"--source={base}", "--staged", "--worktree", "--", f)
        else:
            git("rm", "-q", "--cached", "-f", "--", f, check=False)
            (REPO_ROOT / f).unlink(missing_ok=True)


def commit(message: str) -> str:
    stage_all()
    git("commit", "-q", "-m", message)
    return head()


def save_patch(base: str, path: Path) -> None:
    stage_all()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(git("diff", "--cached", "--binary", base), encoding="utf-8")


def rollback(base: str) -> None:
    git("reset", "-q", "--hard", base)
    git("clean", "-q", "-fd")        # ohne -x: ignorierte Dateien (.env, node_modules, .autopilot) bleiben
