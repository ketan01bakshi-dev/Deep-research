"""Resolve Node.js CLI binaries on Windows (avoids PowerShell .ps1 execution policy)."""

from __future__ import annotations

import os
import platform
import shutil
from contextvars import ContextVar
from pathlib import Path

_node_project_root: ContextVar[Path | None] = ContextVar("node_project_root", default=None)


def set_node_project_root(root: Path | str) -> None:
    _node_project_root.set(Path(root).resolve())


def _project_root() -> Path:
    root = _node_project_root.get()
    if root is not None:
        return root
    from cursor_agent_core.paths.project_context import get_project_root

    return get_project_root()


def puppeteer_cache_dir() -> Path:
    return _project_root() / ".puppeteer-cache"


def _windows_node_bin(name: str) -> str | None:
    for candidate in (
        shutil.which(f"{name}.cmd"),
        shutil.which(f"{name}.exe"),
    ):
        if candidate:
            return candidate

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    default = Path(program_files) / "nodejs" / f"{name}.cmd"
    if default.exists():
        return str(default)
    return None


def resolve_npm() -> str:
    if platform.system() == "Windows":
        path = _windows_node_bin("npm")
        if path:
            return path
        raise RuntimeError(
            "npm.cmd not found. Install Node.js or run D:\\Agents\\install_windows_dev.cmd"
        )

    path = shutil.which("npm")
    if path:
        return path
    raise RuntimeError("npm not found.")


def resolve_npx() -> str:
    if platform.system() == "Windows":
        path = _windows_node_bin("npx")
        if path:
            return path
        raise RuntimeError(
            "npx.cmd not found. Install Node.js or run D:\\Agents\\install_windows_dev.cmd"
        )

    path = shutil.which("npx")
    if path:
        return path
    raise RuntimeError("npx not found. Install Node.js to render Mermaid diagrams.")


def resolve_local_mmdc() -> str | None:
    root = _project_root()
    bin_dir = root / "node_modules" / ".bin"
    if platform.system() == "Windows":
        candidates = (bin_dir / "mmdc.cmd", bin_dir / "mmdc.exe", bin_dir / "mmdc")
    else:
        candidates = (bin_dir / "mmdc",)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def build_mmdc_command(
    mmd_path: Path | str,
    output_path: Path | str,
    *,
    output_format: str = "png",
) -> list[str]:
    mmd = str(mmd_path)
    output = str(output_path)

    local_mmdc = resolve_local_mmdc()
    if local_mmdc:
        command = [local_mmdc, "-i", mmd, "-o", output]
    else:
        command = [
            resolve_npx(),
            "-y",
            "@mermaid-js/mermaid-cli",
            "-i",
            mmd,
            "-o",
            output,
        ]

    if output_format == "svg":
        command.extend(["-e", "svg"])
    return command


def _find_chrome_executable() -> str | None:
    cache_root = puppeteer_cache_dir()
    if cache_root.exists():
        for exe in cache_root.rglob("chrome-headless-shell.exe"):
            return str(exe)
        for exe in cache_root.rglob("chrome.exe"):
            return str(exe)

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    for base in (program_files, program_files_x86):
        chrome = Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
        if chrome.exists():
            return str(chrome)
    return None


def mmdc_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    cache_dir = puppeteer_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env["PUPPETEER_CACHE_DIR"] = str(cache_dir)

    chrome = _find_chrome_executable()
    if chrome:
        env["PUPPETEER_EXECUTABLE_PATH"] = chrome
    return env
