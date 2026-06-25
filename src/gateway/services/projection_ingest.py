"""Vision/code projection ingest — AST in gateway, vision/register via hooks."""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple


from .projection_register import ProjectionRegisterService


@dataclass(frozen=True)
class ProjectionIngestHooks:
    analyze_architecture_image: Callable[[str], Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]


class ProjectionIngestService:
    def __init__(self, hooks: ProjectionIngestHooks, register: ProjectionRegisterService):
        self._hooks = hooks
        self._register = register

    def ingest_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        image_b64 = data.get("image_base64") or data.get("image") or ""
        nodes, links = self._hooks.analyze_architecture_image(str(image_b64))
        if not nodes:
            return {
                "ok": False,
                "error": "vision_analysis_empty",
                "detail": "Ollama vision unavailable or no relationships parsed",
            }
        cluster = f"vision-{int(time.time() * 1000)}"
        node_ids = self._register.register(nodes, links, cluster, source_kind="vision")
        return {
            "ok": True,
            "nodes": len(nodes),
            "links": len(links),
            "node_ids": node_ids,
            "projection_links": links,
        }

    def ingest_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        content = data.get("content") or data.get("source") or ""
        file_name = data.get("file_name") or data.get("filename") or "snippet.py"
        if not str(content).strip():
            return {"ok": False, "error": "missing content"}
        result = project_code_ast(str(content), str(file_name))
        nodes = result.get("nodes") or []
        links = result.get("links") or []
        if not nodes:
            return {
                "ok": False,
                "error": result.get("error") or "ast_empty",
                "detail": "No classes or functions found",
            }
        cluster = f"code:{file_name}"
        node_ids = self._register.register(nodes, links, cluster, source_kind="code")
        return {
            "ok": True,
            "file": file_name,
            "nodes": len(nodes),
            "links": len(links),
            "node_ids": node_ids,
            "projection_links": links,
            "ast_error": result.get("error"),
        }


def project_code_ast(file_content: str, file_name: str) -> Dict[str, Any]:
    """Stdlib AST projection — classes, functions, inheritance."""
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []
    file_name = str(file_name or "snippet.py").strip() or "snippet.py"
    try:
        tree = ast.parse(file_content or "", filename=file_name)
    except SyntaxError as se:
        return {"nodes": nodes, "links": links, "error": str(se)}
    except Exception as exc:
        return {"nodes": nodes, "links": links, "error": str(exc)}

    class_stack: List[str] = []

    class _AstProjector(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            class_id = f"class:{file_name}:{node.name}"
            nodes.append(
                {
                    "id": class_id,
                    "label": f"Class: {node.name}",
                    "title": f"Class: {node.name}",
                    "type": "code_class",
                    "file": file_name,
                }
            )
            for base in node.bases:
                base_name = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name:
                    target = f"class_inherits:{base_name}"
                    links.append({"source": class_id, "target": target, "type": "inherits"})
                    nodes.append(
                        {
                            "id": target,
                            "label": f"Ext: {base_name}",
                            "title": f"Ext: {base_name}",
                            "type": "code_class",
                            "file": file_name,
                        }
                    )
            class_stack.append(node.name)
            self.generic_visit(node)
            class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            func_id = f"func:{file_name}:{node.name}"
            nodes.append(
                {
                    "id": func_id,
                    "label": f"Def: {node.name}()",
                    "title": f"Def: {node.name}()",
                    "type": "code_function",
                    "file": file_name,
                }
            )
            if class_stack:
                parent_id = f"class:{file_name}:{class_stack[-1]}"
                links.append({"source": parent_id, "target": func_id, "type": "defines"})
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            func_id = f"func:{file_name}:{node.name}"
            nodes.append(
                {
                    "id": func_id,
                    "label": f"Def: {node.name}()",
                    "title": f"Def: {node.name}()",
                    "type": "code_function",
                    "file": file_name,
                }
            )
            if class_stack:
                parent_id = f"class:{file_name}:{class_stack[-1]}"
                links.append({"source": parent_id, "target": func_id, "type": "defines"})
            self.generic_visit(node)

    _AstProjector().visit(tree)
    dedup = {n["id"]: n for n in nodes}
    return {"nodes": list(dedup.values()), "links": links, "file": file_name}
