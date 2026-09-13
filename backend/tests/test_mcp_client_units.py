# Unit tests for retrieval plumbing: filter fail-closed behavior and MCP-client
# result normalization + arg coercion. No Weaviate/servers needed.

import pytest

from app.agent.mcp_client import _normalize_result, coerce_args


class _FakeTool:
    def __init__(self, args_schema):
        self.args_schema = args_schema
        self.name = "fake"
        self.description = "fake tool"


def test_normalize_result_dict_passthrough():
    assert _normalize_result({"a": 1}) == {"a": 1}


def test_normalize_result_json_string():
    assert _normalize_result('{"a": 1}') == {"a": 1}


def test_normalize_result_content_blocks():
    blocks = [{"type": "text", "text": '{"a": 1}'}]
    assert _normalize_result(blocks) == {"a": 1}


def test_normalize_result_plain_text_list():
    blocks = ["hello", "world"]
    assert _normalize_result(blocks) == {"result": "hello\nworld"}


def test_normalize_result_other():
    assert _normalize_result(42) == {"result": 42}


def test_coerce_args_int_float_bool():
    tool = _FakeTool(
        {
            "type": "object",
            "properties": {
                "top_k": {"type": "integer"},
                "ctc": {"type": "number"},
                "flag": {"type": "boolean"},
                "name": {"type": "string"},
            },
        }
    )
    args = {"top_k": "5", "ctc": "12.5", "flag": "true", "name": "abc", "extra": "kept"}
    out = coerce_args(tool, args)
    assert out["top_k"] == 5
    assert out["ctc"] == 12.5
    assert out["flag"] is True
    assert out["name"] == "abc"
    assert out["extra"] == "kept"  # unknown args passed through untouched


def test_coerce_args_bad_number_passes_through():
    tool = _FakeTool({"type": "object", "properties": {"top_k": {"type": "integer"}}})
    out = coerce_args(tool, {"top_k": "not-a-number"})
    assert out["top_k"] == "not-a-number"


def test_coerce_args_no_schema():
    tool = _FakeTool(None)
    args = {"a": "1"}
    assert coerce_args(tool, args) == args


def test_build_filter_unknown_key_fails_closed():
    from app.ai.retriever import _build_filter

    with pytest.raises(ValueError, match="unsupported filter keys"):
        _build_filter({"evil_key": "x"})


def test_build_filter_known_keys():
    from app.ai.retriever import _build_filter

    assert _build_filter({}) is None
    assert _build_filter(None) is None
    assert _build_filter({"company": "", "document_type": None}) is None
    f = _build_filter({"company": "TCS"})
    assert f is not None


def test_build_filter_requires_weaviate():
    pytest.importorskip("weaviate")
    from app.ai.retriever import _build_filter

    f = _build_filter({"company": ["TCS", "Infosys"], "year": 2026})
    assert f is not None
