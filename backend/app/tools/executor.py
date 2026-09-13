"""Controlled execution boundary for registered local Phase 5 tools.

The only execution path is: LLM/controller request -> registered-tool lookup ->
Pydantic argument validation -> enabled-policy check -> explicit local handler
-> structured observation. Permission metadata describes each tool's risk class;
the currently implemented executable policy is the registry's ``enabled`` flag.
"""

from typing import Any

from app.services.documents.document_service import document_service
from app.services.knowledge.knowledge_service import knowledge_service
from app.services.sandbox_service import sandbox_service
from app.services.data_analysis_service import data_analysis_service
from app.services.deliverable_service import deliverable_service
from app.tools.registry import TOOLS
from app.tools.schemas import (
    CalculatorInput,
    DataSourcesInput,
    DocumentIdInput,
    KnowledgeSearchInput,
    ToolResult,
    SandboxCodeInput,
)
from app.schemas.analysis import DataAnalysisRequest
from app.schemas.deliverables import ChartSpec, DocumentSpec, TableSpec


class ToolExecutor:
    """Validate and execute only fixed, local, policy-approved tool operations.

    Tool names and arguments are always treated as untrusted controller or LLM
    output. This class deliberately uses explicit branches instead of callable
    lookup, reflection, dynamic imports, shell execution, ``eval``, or ``exec``.
    """

    def execute(self, tool_id: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute one registered tool and return a normalized observation.

        Args:
            tool_id: Untrusted requested identifier, checked against the fixed
                registry before any operation can occur.
            arguments: Untrusted structured values validated by the registered
                tool's Pydantic schema.

        Returns:
            Structured success or failure output; ordinary execution failures
            become observations rather than escaping the bounded agent flow.
        """
        # SECURITY: an LLM cannot map a generated name to arbitrary Python,
        # shell commands, files, imports, eval, exec, or dynamic callables.
        tool = TOOLS.get(tool_id)
        if not tool:
            return ToolResult(tool=tool_id, success=False, error="Unknown tool.")
        # The enabled flag is the executable policy check. Permission labels
        # remain auditable risk metadata for the fixed approved registry.
        if not tool.enabled:
            return ToolResult(tool=tool_id, success=False, error="Tool is disabled.")

        try:
            validated_arguments = tool.schema.model_validate(arguments)
            if tool_id == "knowledge_search":
                return self._search_knowledge(validated_arguments)
            if tool_id == "document_metadata":
                return self._read_document_metadata(validated_arguments)
            if tool_id == "document_text":
                return self._read_document_text(validated_arguments)
            if tool_id == "list_data_sources":
                return self._list_data_sources(validated_arguments)
            if tool_id == "python_sandbox":
                return self._sandbox(validated_arguments)
            if tool_id == "data_analysis":
                return self._analyze(validated_arguments)
            if tool_id == "create_chart": return self._artifact("create_chart", deliverable_service.create_chart(validated_arguments))
            if tool_id == "create_spreadsheet": return self._artifact("create_spreadsheet", deliverable_service.create_spreadsheet(validated_arguments))
            if tool_id == "create_document": return self._artifact("create_document", deliverable_service.create_document(validated_arguments))
            if tool_id == "create_presentation": return self._artifact("create_presentation", deliverable_service.create_presentation(validated_arguments))
            if tool_id == "create_pdf": return self._artifact("create_pdf", deliverable_service.create_pdf(validated_arguments))
            return self._calculate(validated_arguments)
        except Exception as error:
            return ToolResult(tool=tool_id, success=False, error=str(error))

    @staticmethod
    def _search_knowledge(arguments: KnowledgeSearchInput) -> ToolResult:
        """Run local knowledge retrieval and propagate traceable source IDs.

        Args:
            arguments: Validated query and bounded result limit.

        Returns:
            Retrieved local chunks and source records for the agent response.
        """
        results = knowledge_service.search(arguments.query, arguments.top_k)
        return ToolResult(
            tool="knowledge_search",
            success=True,
            data={"results": results},
            sources=[
                {
                    key: result[key]
                    for key in ("document_id", "filename", "chunk_id")
                }
                for result in results
            ],
        )

    @staticmethod
    def _read_document_metadata(arguments: DocumentIdInput) -> ToolResult:
        """Read validated metadata for one locally controlled document.

        Args:
            arguments: Validated server-issued document identifier.

        Returns:
            Serialized document metadata observation.
        """
        return ToolResult(
            tool="document_metadata",
            success=True,
            data=document_service.get_metadata(arguments.document_id).model_dump(mode="json"),
        )

    @staticmethod
    def _read_document_text(arguments: DocumentIdInput) -> ToolResult:
        """Read a bounded excerpt of extracted local document text.

        Args:
            arguments: Validated server-issued document identifier.

        Returns:
            An observation with at most 12,000 extracted-text characters.
        """
        # SECURITY: the bounded excerpt prevents a tool result from expanding
        # an agent context with an unbounded locally stored document.
        return ToolResult(
            tool="document_text",
            success=True,
            data={"text": document_service.get_text(arguments.document_id)[:12_000]},
        )

    @staticmethod
    def _list_data_sources(arguments: DataSourcesInput) -> ToolResult:
        """Enumerate application-managed structured inputs for the planner.

        The returned records contain no filesystem paths. IDs remain an internal
        tool-to-tool reference and are never rendered in the normal TUI.
        """
        del arguments
        datasets = []
        for metadata in document_service.list_documents():
            if metadata.file_type not in {"csv", "xlsx"}:
                continue
            structured = metadata.structured_metadata if isinstance(metadata.structured_metadata, dict) else {}
            columns = structured.get("columns", [])
            datasets.append({
                "source_kind": "document",
                "source_id": metadata.document_id,
                "filename": metadata.filename,
                "file_type": metadata.file_type,
                "columns": columns if isinstance(columns, list) else [],
            })
        return ToolResult(tool="list_data_sources", success=True, data={"datasets": datasets})

    @staticmethod
    def _calculate(arguments: CalculatorInput) -> ToolResult:
        """Perform a fixed arithmetic operation without evaluating expressions.

        Args:
            arguments: Validated operation name and finite operand collection.

        Returns:
            Numeric result wrapped as a successful calculator observation.
        """
        values = arguments.values
        if arguments.operation == "add":
            result = sum(values)
        elif arguments.operation == "subtract":
            result = values[0] - sum(values[1:])
        elif arguments.operation == "multiply":
            result = 1.0
            for value in values:
                result *= value
        elif arguments.operation == "divide":
            result = values[0]
            for value in values[1:]:
                if value == 0:
                    raise ValueError("Division by zero.")
                result /= value
        elif arguments.operation == "percentage":
            if len(values) != 2:
                raise ValueError("Percentage requires value and percent.")
            result = values[0] * values[1] / 100
        else:
            result = sum(values) / len(values)
        return ToolResult(tool="calculator", success=True, data={"result": result})

    @staticmethod
    def _sandbox(arguments: SandboxCodeInput) -> ToolResult:
        result = sandbox_service.execute(arguments.code)
        return ToolResult(tool="python_sandbox", success=result.status == "success", data={"execution_id": result.execution_id, "stdout": result.stdout, "artifacts": [item.model_dump() for item in result.artifacts], "job_id": result.job_id}, error=None if result.status == "success" else result.stderr)

    @staticmethod
    def _analyze(arguments: DataAnalysisRequest) -> ToolResult:
        result = data_analysis_service.analyze(arguments)
        data = result.model_dump(mode="json")
        data["request"] = arguments.model_dump(mode="json")
        return ToolResult(tool="data_analysis", success=True, data=data)

    @staticmethod
    def _artifact(tool: str, artifact: object) -> ToolResult:
        return ToolResult(tool=tool, success=True, data={"artifact": artifact.model_dump(mode="json")})


tool_executor = ToolExecutor()
