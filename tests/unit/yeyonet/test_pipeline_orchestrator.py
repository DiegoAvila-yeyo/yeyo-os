import json

from src.yeyonet.pipeline_orchestrator import _json_value, _row_to_dict


def test_json_value_decodes_json_strings():
    assert _json_value('{"prompt":"hola"}', {}) == {"prompt": "hola"}
    assert _json_value('["a","b"]', []) == ["a", "b"]


def test_row_to_dict_decodes_json_columns():
    row = {
        "id": "run-1",
        "ring_node_ids": json.dumps(["central", "sat"]),
        "input_payload": json.dumps({"prompt": "hola"}),
        "output_payload": json.dumps({"status": "completed"}),
    }

    data = _row_to_dict(row)

    assert data["ring_node_ids"] == ["central", "sat"]
    assert data["input_payload"] == {"prompt": "hola"}
    assert data["output_payload"] == {"status": "completed"}
