import json
import types
from pathlib import Path

# Import the function's main module
import importlib.util


def load_module(mod_path: str):
    spec = importlib.util.spec_from_file_location("write_predictions", mod_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_json_list():
    mod = load_module(
        str(
            Path("functions/adt_ingest/write_predictions/__init__.py").resolve()
        )
    )

    # Build a fake request object similar to azure.functions.HttpRequest
    class FakeReq:
        def __init__(self, body: bytes):
            self._body = body

        def get_body(self):
            return self._body

    payload = [
        {
            "adtSegmentId": "segment-001",
            "congestionIndex": 0.5,
            "confidence": 0.8,
            "timestamp": 1733090000,
        },
        {
            "adtSegmentId": "segment-002",
            "congestionIndex": 0.7,
            "confidence": 0.85,
            "timestamp": 1733090001,
        },
    ]

    req = FakeReq(json.dumps(payload).encode("utf-8"))

    # Monkeypatch shared.get_clients to avoid real Azure calls
    class FakeADTClient:
        def __init__(self):
            self.patches = []

        def update_digital_twin(self, twin_id, ops):
            self.patches.append((twin_id, ops))

    class FakeBlobClient:
        pass

    fake_adt = FakeADTClient()
    fake_blob = FakeBlobClient()

    fake_shared = types.SimpleNamespace(get_clients=lambda: (fake_adt, fake_blob))

    # Inject our fake shared module
    mod.shared = fake_shared

    # Execute the handler
    resp = mod.main(req)

    # Validate that patches were constructed for both entries
    assert hasattr(fake_adt, "patches")
    assert len(fake_adt.patches) == 2
    assert resp is not None
