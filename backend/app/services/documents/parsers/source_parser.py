"""Inert Python and Markdown extraction for local knowledge ingestion."""
import ast
import re

from app.services.documents.parsers.text_parser import extract_text


def extract_python(content: bytes) -> tuple[str, dict[str, object]]:
    """Decode source as text only; AST inspection is optional metadata, never execution."""
    text = extract_text(content)
    metadata: dict[str, object] = {"language": "Python", "line_count": len(text.splitlines())}
    try:
        tree = ast.parse(text)
        metadata["functions"] = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        metadata["classes"] = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    except SyntaxError:
        metadata["syntax_valid"] = False
    return text, metadata


def extract_markdown(content: bytes) -> tuple[str, dict[str, object]]:
    """Preserve readable Markdown exactly as text; code fences are inert content."""
    text = extract_text(content)
    headings = [match.group(2).strip() for match in re.finditer(r"^(#{1,6})\s+(.+)$", text, flags=re.MULTILINE)]
    return text, {"language": "Markdown", "headings": headings, "section_count": len(headings), "line_count": len(text.splitlines())}
