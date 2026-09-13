"""Bounded subprocess Python execution in a server-created local workspace.

This is practical process/workspace isolation, not a container or VM. Phase 8
must add stronger OS/network policy for hostile-code security guarantees.
"""

import ast
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from app.core.config import settings
from app.schemas.sandbox import SandboxArtifact, SandboxExecutionResult
from app.services.artifact_service import artifact_service
from app.services.jobs import job_progress_service
from app.services.llm.task_classifier import task_classifier
from app.services.llm.model_router import model_router
from app.services.llm.ollama_service import ollama_service

BLOCKED_IMPORTS = {"os", "subprocess", "socket", "requests", "urllib", "http", "ftplib", "pathlib", "shutil", "ctypes", "multiprocessing"}
BLOCKED_NAMES = {"eval", "exec", "compile", "open", "input", "__import__", "globals", "locals", "vars", "breakpoint"}


class SandboxService:
    """Run validated code outside the FastAPI process with strict local limits."""

    def execute(self, code: str) -> SandboxExecutionResult:
        """Execute source in an empty workspace and capture bounded output."""
        job = job_progress_service.create("sandbox_execution", "preparing_code", "Preparing bounded local code execution.", display_name="Python workspace", resource_type="sandbox")
        execution_id = str(uuid.uuid4())
        workspace = settings.data_directory / "sandbox" / execution_id
        started = time.perf_counter()
        try:
            job_progress_service.update(job.job_id, "running", "validating_code", "Validating execution policy.", 15)
            reason = self._validate(code)
            if reason:
                job_progress_service.update(job.job_id, "failed", "failed", "Code was rejected by sandbox policy.", 100)
                return SandboxExecutionResult(execution_id=execution_id, status="rejected", stderr=reason, duration_ms=0, job_id=job.job_id)
            job_progress_service.update(job.job_id, "running", "preparing_sandbox", "Creating isolated local workspace.", 30)
            workspace.mkdir(parents=True, exist_ok=False)
            (workspace / "main.py").write_text(code, encoding="utf-8")
            job_progress_service.update(job.job_id, "running", "executing_code", "Executing code in restricted subprocess.", 55)
            # SECURITY: no shell, controlled cwd/env, no inherited secrets.
            completed = subprocess.run([sys.executable, "-I", "-B", "main.py"], cwd=workspace, env={"PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1", "PATH": os.environ.get("SystemRoot", "")}, capture_output=True, text=False, timeout=settings.sandbox_timeout_seconds)
            job_progress_service.update(job.job_id, "running", "verifying_execution", "Capturing and validating generated artifacts.", 85)
            stdout, stderr = self._limit(completed.stdout), self._safe_error(completed.stderr)
            status = "success" if completed.returncode == 0 else "failed"
            result = SandboxExecutionResult(execution_id=execution_id, status=status, stdout=stdout, stderr=stderr, exit_code=completed.returncode, duration_ms=(time.perf_counter()-started)*1000, artifacts=self._artifacts(workspace, job.job_id), job_id=job.job_id)
            job_progress_service.update(job.job_id, "completed" if status == "success" else "failed", "completed" if status == "success" else "failed", "Sandbox execution completed." if status == "success" else "Sandbox execution failed safely.", 100)
            return result
        except subprocess.TimeoutExpired as error:
            job_progress_service.update(job.job_id, "failed", "failed", "Execution exceeded the configured timeout.", 100)
            return SandboxExecutionResult(execution_id=execution_id, status="timeout", stdout=self._limit(error.stdout or b""), stderr="Execution exceeded the configured timeout.", duration_ms=(time.perf_counter()-started)*1000, job_id=job.job_id)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def generate_and_execute(self, task: str) -> SandboxExecutionResult:
        """Use the registered local coding model and bounded safe-error repair."""
        classification = task_classifier.classify(task)
        model, _ = model_router.route(classification, override_model_id="coding")
        prompt = "Write only Python code for this task. No imports that access OS, network, files, shell, or environment. Use print for output. Task: " + task
        code = self._code_only(ollama_service.chat_with_model(model.ollama_model, prompt))
        result = self.execute(code)
        for _ in range(settings.sandbox_max_repair_attempts):
            if result.status == "success": break
            repair = "Return only corrected Python code. It must obey the same restrictions. Task: " + task + "\nSafe execution error:\n" + result.stderr[:2000]
            code = self._code_only(ollama_service.chat_with_model(model.ollama_model, repair))
            result = self.execute(code)
        return result

    @staticmethod
    def _code_only(response: str) -> str:
        """Strip an optional Markdown fence before the sandbox validation step."""
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1] if "\n" in response else ""
            response = response.rsplit("```", 1)[0]
        return response.strip()

    def _limit(self, value: str | bytes) -> str:
        """Cap captured output without leaking oversized process output."""
        text = value.decode("utf-8", "replace") if isinstance(value, bytes) else value
        encoded = text.encode("utf-8")
        suffix = "\n[output truncated]" if len(encoded) > settings.sandbox_max_output_bytes else ""
        return encoded[:settings.sandbox_max_output_bytes].decode("utf-8", "ignore") + suffix

    def _safe_error(self, value: str | bytes) -> str:
        """Return a useful runtime diagnostic without a traceback or host path."""
        text = self._limit(value)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # Python's final traceback line contains the exception class and
        # message; prior lines may expose an absolute ephemeral workspace path.
        return lines[-1] if lines else "Python execution failed without an error message."

    def _artifacts(self, workspace: Path, job_id: str) -> list[SandboxArtifact]:
        """Return bounded, workspace-local generated files excluding source."""
        artifacts: list[SandboxArtifact] = []
        for path in workspace.iterdir():
            if path.name == "main.py" or not path.is_file():
                continue
            if path.stat().st_size > settings.sandbox_max_file_bytes or len(artifacts) >= settings.sandbox_max_artifacts:
                continue
            registered = artifact_service.register(path, path.name, "sandbox", "sandbox", job_id=job_id, provenance={"execution_workspace": "ephemeral"})
            artifacts.append(SandboxArtifact(artifact_id=registered.artifact_id, filename=registered.filename, size_bytes=registered.size_bytes))
        return artifacts

    @staticmethod
    def _validate(code: str) -> str | None:
        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            return f"Syntax error: {error.msg}."
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and any(item.name.split(".")[0] in BLOCKED_IMPORTS for item in node.names):
                return "Code imports a module blocked by sandbox policy."
            if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
                return "Code uses an operation blocked by sandbox policy."
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return "Code uses a blocked introspection operation."
        return None


sandbox_service = SandboxService()
