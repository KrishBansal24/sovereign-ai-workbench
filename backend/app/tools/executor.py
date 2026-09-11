"""Controlled execution boundary for registered local Phase 5 tools.

The only execution path is: LLM/controller request -> registered-tool lookup ->
Pydantic argument validation -> enabled-policy check -> explicit local handler
-> structured observation. Permission metadata describes each tool's risk class;
the currently implemented executable policy is the registry's ``enabled`` flag.
"""

from typing import Any

from app.services.documents.document_service import document_service
from app.services.knowledge.knowledge_service import knowledge_service
from app.tools.registry import TOOLS
from app.tools.schemas import (
    CalculatorInput,
    DocumentIdInput,
    KnowledgeSearchInput,
    ToolResult,
)


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


tool_executor = ToolExecutor()
