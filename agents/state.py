from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """Shared state object that flows through every node in the LangGraph pipeline.

    Each agent reads what it needs from here and writes its own output back
    under its own key, so agents never overwrite each other's results.
    """

    inputs: dict[str, Any]

    maude_ingestion_result: dict[str, Any]
    product_identity_result: dict[str, Any]
    regulatory_context_result: dict[str, Any]
    scope_validation_result: dict[str, Any]
    document_impact_result: dict[str, Any]

    errors: list[str]
