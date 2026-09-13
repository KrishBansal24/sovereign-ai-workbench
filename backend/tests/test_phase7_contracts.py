"""Focused Phase 7 contracts that do not require Ollama or external services."""
from app.services.artifact_service import ArtifactService
from app.services.sandbox_service import SandboxService
from app.tools.registry import TOOLS


def test_phase7_tools_are_fixed_and_schema_backed() -> None:
    expected = {"python_sandbox", "data_analysis", "create_chart", "create_spreadsheet", "create_document", "create_presentation", "create_pdf"}
    assert expected <= set(TOOLS)
    assert all(TOOLS[tool_id].schema is not None for tool_id in expected)


def test_sandbox_policy_rejects_syntax_host_io_and_network_imports() -> None:
    assert SandboxService._validate("print(2 + 2)") is None
    assert SandboxService._validate("import socket") is not None
    assert SandboxService._validate("open('host-file.txt')") is not None
    assert SandboxService._validate("def broken(") is not None


def test_sandbox_runtime_error_omits_ephemeral_host_path() -> None:
    """A user-facing runtime error stays useful without exposing a host path."""
    result = SandboxService().execute("print(10 / 0)")

    assert result.status == "failed"
    assert result.stderr == "ZeroDivisionError: division by zero"
    assert "sandbox" not in result.stderr.lower()


def test_artifact_filename_is_a_safe_basename() -> None:
    assert ArtifactService.safe_filename("../../report.xlsx") == "report.xlsx"
    safe_name = ArtifactService.safe_filename("C:\\unsafe\\report.xlsx")
    assert ".." not in safe_name and "/" not in safe_name and "\\" not in safe_name
