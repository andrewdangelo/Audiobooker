#!/usr/bin/env python3
"""
dump_project_minimal.py
=======================
Generates a '/proj-code-dump' directory at the root of your project containing:

  1. tree.txt   — Unicode directory tree of the whole project
  2. Flat copies of all relevant source files (path prefixed with '__')

USAGE:
  python dump_project_minimal.py                   # run from project root
  python dump_project_minimal.py /path/to/project  # or pass the root explicitly

DEPENDENCIES:
  None — stdlib only
"""

import os
import sys
import re
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# 0.  SECURITY — HARD EXCLUSIONS
#     '.env' and variants are unconditionally excluded before anything else.
# ---------------------------------------------------------------------------

HARD_EXCLUDE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
}

# ---------------------------------------------------------------------------
# 1.  SOFT EXCLUSIONS
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "env", ".env_dir",
    ".git", ".svn", ".hg", ".idea", ".vscode",
    "dist", "build",
    "proj-code-dump",
    "node_modules",
}

EXCLUDE_FILE_NAMES = {
    "__init__.py",
    "LICENSE", "LICENSE.txt", "LICENSE.md",
    ".DS_Store", "Thumbs.db",
}

EXCLUDE_FILE_SUFFIXES = {
    ".pyc", ".pyo", ".pyd",
    ".so", ".dll", ".dylib",
    ".egg", ".whl",
    ".log",
    ".sqlite", ".db",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".webp",
    ".mp4", ".mp3", ".wav",
    ".zip", ".tar", ".gz", ".bz2", ".rar",
}

INCLUDE_SUFFIXES = {
    ".py",
    ".txt", ".md", ".rst",
    ".toml", ".cfg", ".ini",
    ".yaml", ".yml",
    ".json",
    ".sh", ".sql",
    ".html", ".jinja", ".j2",
    ".css",
}

ALWAYS_INCLUDE_NAMES = {
    "requirements.txt", "requirements-dev.txt", "requirements-prod.txt",
    "pyproject.toml", "setup.cfg", "setup.py",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "README.md", "README.rst", "README.txt",
    "alembic.ini",
}

# ---------------------------------------------------------------------------
# 2.  TREE BUILDER
# ---------------------------------------------------------------------------

def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS or name.endswith(".egg-info")


def build_tree(root: Path, prefix: str = "", output_dir: Path = None) -> list[str]:
    """Recursively build a Unicode tree, excluding the output dir."""
    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return lines

    entries = [
        e for e in entries
        if not (e.is_dir() and _is_excluded_dir(e.name))
        and not (output_dir and e.resolve() == output_dir.resolve())
    ]

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            lines.extend(build_tree(entry, prefix + extension, output_dir))
    return lines


def write_tree(project_root: Path, output_dir: Path) -> None:
    print("[tree] Building directory tree …")
    lines = [project_root.name + "/"] + build_tree(project_root, output_dir=output_dir)
    (output_dir / "tree.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"[tree] Written → {output_dir / 'tree.txt'}")


# ---------------------------------------------------------------------------
# 3.  FILE COLLECTION
# ---------------------------------------------------------------------------

def should_include(path: Path) -> bool:
    """Return True if a file should be included in the dump."""
    # Hard security check first — never copy .env files
    if path.name in HARD_EXCLUDE_FILES:
        return False
    if re.match(r'^\.env(\..+)?$', path.name) and path.name not in {".env.example", ".env.template"}:
        return False

    if path.name in EXCLUDE_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return False
    if path.name in ALWAYS_INCLUDE_NAMES:
        return True

    return path.suffix.lower() in INCLUDE_SUFFIXES


def collect_files(project_root: Path, output_dir: Path) -> list[Path]:
    """Walk the project and return all files that should be copied."""
    files = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        current = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if not _is_excluded_dir(d)
            and not (output_dir and (current / d).resolve() == output_dir.resolve())
        ]
        for fname in filenames:
            fpath = current / fname
            if should_include(fpath):
                files.append(fpath)

    print(f"[collect] Found {len(files)} relevant files")
    return files


def path_to_flat_name(project_root: Path, file_path: Path) -> str:
    """
    Convert a nested path to a flat filename using '__' as separator.
    e.g. app/routers/users.py → app__routers__users.py
    """
    rel = file_path.relative_to(project_root)
    parts = [p.replace("__", "_") for p in rel.parts]
    return "__".join(parts)


def copy_files(project_root: Path, files: list[Path], output_dir: Path) -> None:
    print(f"[copy] Copying {len(files)} files …")
    for i, fpath in enumerate(files, 1):
        dest_name = path_to_flat_name(project_root, fpath)
        shutil.copy2(fpath, output_dir / dest_name)
        print(f"[copy] ({i}/{len(files)}) {dest_name}")
    print("[copy] Done")


# ---------------------------------------------------------------------------
# 4.  MAIN
# ---------------------------------------------------------------------------

def main():
    # Hard security gate — fail immediately if somehow .env slipped through
    assert ".env" in HARD_EXCLUDE_FILES, "FATAL: .env is not in HARD_EXCLUDE_FILES!"

    project_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    print(f"\n{'='*60}")
    print(f"  Project root : {project_root}")
    print(f"{'='*60}\n")

    output_dir = project_root / "proj-code-dump"
    if output_dir.exists():
        print(f"[setup] Clearing previous dump …")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    write_tree(project_root, output_dir)
    files = collect_files(project_root, output_dir)
    copy_files(project_root, files, output_dir)

    dumped = list(output_dir.iterdir())
    print(f"\n{'='*60}")
    print(f"  Done! {len(dumped)} files in {output_dir}")
    print(f"  • tree.txt")
    print(f"  • {len(dumped) - 1} source file copies")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()