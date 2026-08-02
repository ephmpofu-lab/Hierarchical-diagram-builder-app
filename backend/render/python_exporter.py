"""Python Package Exporter (10g) -- packages the Python Renderer's ordered code blocks into
a real, downloadable zip of the domain's module structure
(architeq_{domain}/{layer_slug}/{sub_task_slug}.py). Mirrors n8n_exporter.py's role for the
n8n track: the renderer computes content, this wraps it into the final downloadable
artifact -- never recomputing code, never a second source of truth."""

import io
import zipfile
from typing import Dict, List

from ..models import DomainTaskTree, RenderedCodeBlock
from .python_renderer import _function_name, render_python


def _group_blocks_by_folder_and_file(
    tree: DomainTaskTree, blocks: List[RenderedCodeBlock]
) -> Dict[str, Dict[str, List[RenderedCodeBlock]]]:
    """Folder = Layer, file = Sub-task -- mirrors decompose.js::groupPythonRenderByFile
    exactly, now computed server-side for the real zip export. A block whose parent chain
    can't be resolved (shouldn't happen given R2's C4 nesting) never gets silently dropped,
    same posture as the frontend's own "(root)"/"(unresolved)" fallback."""
    grouped: Dict[str, Dict[str, List[RenderedCodeBlock]]] = {}
    for block in blocks:
        atomic = tree.nodes.get(block.step_id)
        sub_task = tree.nodes.get(atomic.parent_id) if atomic and atomic.parent_id else None
        layer = tree.nodes.get(sub_task.parent_id) if sub_task and sub_task.parent_id else None
        folder_label = layer.label if layer else "(root)"
        file_label = sub_task.label if sub_task else "(unresolved)"
        grouped.setdefault(folder_label, {}).setdefault(file_label, []).append(block)
    return grouped


def export_python_package(domain: str, tree: DomainTaskTree) -> bytes:
    blocks = render_python(tree)
    grouped = _group_blocks_by_folder_and_file(tree, blocks)
    package_name = f"architeq_{_function_name(domain)}"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{package_name}/__init__.py", "")
        for folder_label, files in grouped.items():
            folder_slug = _function_name(folder_label)
            zf.writestr(f"{package_name}/{folder_slug}/__init__.py", "")
            for file_label, file_blocks in files.items():
                file_slug = _function_name(file_label)
                content = "\n\n\n".join(block.code for block in file_blocks) + "\n"
                zf.writestr(f"{package_name}/{folder_slug}/{file_slug}.py", content)
    return buffer.getvalue()
