"""Create diagrams from Mermaid source and render to PNG/SVG."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from cursor_sdk import CustomTool, CustomToolContext

from cursor_agent_core.node.cli import (
    build_mmdc_command,
    mmdc_subprocess_env,
    resolve_local_mmdc,
    resolve_npx,
)
from cursor_agent_core.paths.file_helpers import (
    relative_to_project,
    sanitize_filename,
    slugify,
    unique_path,
    utc_timestamp,
)
from cursor_agent_core.paths.project_context import get_output_directory, get_project_root

_VALID_FORMATS = {"png", "svg", "both"}
_VALID_DIAGRAM_TYPES = {"mindmap", "flowchart", "sequence", "other"}
_MERMAID_TYPE_PREFIXES = ("mindmap", "flowchart", "sequenceDiagram", "graph", "classDiagram")


def _indent_mindmap_children(children: Any, depth: int) -> list[str]:
    lines: list[str] = []
    prefix = "  " * depth
    if not isinstance(children, list):
        return lines
    for child in children:
        if isinstance(child, dict):
            label = str(child.get("label") or "").strip()
            if not label:
                continue
            lines.append(f"{prefix}{label}")
            nested = child.get("children")
            if nested:
                lines.extend(_indent_mindmap_children(nested, depth + 1))
        else:
            text = str(child).strip()
            if text:
                lines.append(f"{prefix}{text}")
    return lines


def _build_mindmap_from_branches(title: str, branches: Any) -> str:
    if not isinstance(branches, list) or not branches:
        raise ValueError("branches must be a non-empty list when mermaid_source is omitted")

    root = title.strip() or "Topic"
    lines = ["mindmap", f"  root(({root}))"]
    lines.extend(_indent_mindmap_children(branches, 2))
    return "\n".join(lines) + "\n"


def _ensure_mindmap_default(source: str, title: str, diagram_type: str) -> str:
    text = source.strip()
    if diagram_type != "mindmap":
        return f"{text}\n"

    lowered = text.lower()
    if any(lowered.startswith(prefix.lower()) for prefix in _MERMAID_TYPE_PREFIXES):
        return f"{text}\n"

    root = title.strip() or "Topic"
    body_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not body_lines:
        return f"mindmap\n  root(({root}))\n"

    lines = ["mindmap", f"  root(({root}))"]
    for line in body_lines:
        if line.startswith(("-", "*")):
            lines.append(f"  {line.lstrip('-* ')}")
        else:
            lines.append(f"    {line}")
    return "\n".join(lines) + "\n"


def _normalize_mermaid(
    source: str,
    *,
    title: str,
    diagram_type: str,
    branches: Any = None,
) -> str:
    if source.strip():
        return _ensure_mindmap_default(source, title, diagram_type)
    if diagram_type == "mindmap":
        return _build_mindmap_from_branches(title, branches)
    raise ValueError("mermaid_source or branches is required")


def _render_with_mmdc(mmd_path: Any, output_path: Any, fmt: str) -> None:
    try:
        command = build_mmdc_command(mmd_path, output_path, output_format=fmt)
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc} On Windows PowerShell, use npx.cmd (not npx) or run: "
            'npm.cmd install in the project folder.'
        ) from exc

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        shell=False,
        env=mmdc_subprocess_env(),
        cwd=str(get_project_root()),
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "mmdc render failed").strip()
        raise RuntimeError(stderr)


def create_diagram(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """Write Mermaid source and render diagram files in the session Diagrams/ folder."""
    title = str(args.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")

    diagram_type = str(args.get("diagram_type") or "mindmap").strip().lower()
    if diagram_type not in _VALID_DIAGRAM_TYPES:
        raise ValueError("diagram_type must be mindmap, flowchart, sequence, or other")

    mermaid_source = _normalize_mermaid(
        str(args.get("mermaid_source") or ""),
        title=title,
        diagram_type=diagram_type,
        branches=args.get("branches"),
    )
    output_format = str(args.get("output_format") or "png").strip().lower()
    if output_format not in _VALID_FORMATS:
        raise ValueError("output_format must be png, svg, or both")

    directory = get_output_directory('diagrams')
    base_name = slugify(title)
    if diagram_type == "mindmap" and not base_name.endswith("-mindmap"):
        base_name = f"{base_name}-mindmap"
    mmd_path = unique_path(directory, f"{base_name}.mmd")
    mmd_path.write_text(mermaid_source, encoding="utf-8")

    outputs: dict[str, str | None] = {
        "mmd_path": relative_to_project(mmd_path, get_project_root()),
        "png_path": None,
        "svg_path": None,
    }
    render_errors: list[str] = []

    formats_to_render: list[str]
    if output_format == "both":
        formats_to_render = ["png", "svg"]
    else:
        formats_to_render = [output_format]

    for fmt in formats_to_render:
        out_path = mmd_path.with_suffix(f".{fmt}")
        try:
            _render_with_mmdc(mmd_path, out_path, fmt)
            outputs[f"{fmt}_path"] = relative_to_project(out_path, get_project_root())
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
            render_errors.append(f"{fmt}: {exc}")

    payload = {
        "title": title,
        "diagram_type": diagram_type,
        "diagrams_directory": relative_to_project(directory, get_project_root()),
        **outputs,
    }
    if render_errors:
        payload["render_warnings"] = render_errors
        payload["mmdc"] = resolve_local_mmdc() or resolve_npx()
        payload["note"] = (
            "Mermaid source was saved. Run setup_diagrams.cmd "
            "(or D:\\Agents\\install_windows_dev.cmd for laptop-wide npm/npx fix)."
        )

    return json.dumps(payload, indent=2)


CREATE_DIAGRAM_TOOL = CustomTool(
    execute=create_diagram,
    description=(
        "Create a visual diagram in the session Diagrams/ folder. Default and preferred format is "
        "Mermaid mindmap (diagram_type=mindmap). Renders PNG/SVG images. Use branches "
        "for structured mind maps or mermaid_source with mindmap syntax."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Diagram / mind map central topic."},
            "diagram_type": {
                "type": "string",
                "enum": ["mindmap", "flowchart", "sequence", "other"],
                "description": "Diagram style. Default mindmap — always prefer unless user asks otherwise.",
            },
            "branches": {
                "type": "array",
                "description": (
                    "Mind map branches (alternative to mermaid_source). Each item: "
                    "{label, children?: [...]}"
                ),
                "items": {"type": "object"},
            },
            "mermaid_source": {
                "type": "string",
                "description": (
                    "Mermaid source. For mind maps use mindmap syntax with root((Topic)) "
                    "and indented branches."
                ),
            },
            "output_format": {
                "type": "string",
                "enum": ["png", "svg", "both"],
                "description": "Rendered image format (default png).",
            },
        },
        "required": ["title"],
    },
)
