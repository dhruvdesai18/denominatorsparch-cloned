import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.pipeline import build_pipeline_graph


def test_pipeline_compiles():
    pipeline = build_pipeline_graph()
    assert pipeline is not None


def test_pipeline_runs_end_to_end_with_placeholders():
    pipeline = build_pipeline_graph()
    final_state = pipeline.invoke({"inputs": {}, "errors": []})

    expected_keys = [
        "maude_ingestion_result",
        "product_identity_result",
        "regulatory_context_result",
        "scope_validation_result",
        "document_impact_result",
    ]
    for key in expected_keys:
        assert key in final_state
        assert final_state[key]["status"] == "pending"

    assert len(final_state["errors"]) == 5
