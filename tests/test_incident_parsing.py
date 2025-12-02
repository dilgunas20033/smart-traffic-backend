import importlib.util
from pathlib import Path


def load_module(mod_path: str):
    spec = importlib.util.spec_from_file_location("fetch_ritis_incidents", mod_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_lane_status_basic():
    mod = load_module(
        str(
            Path("functions/adt_ingest/fetch_ritis_incidents/__init__.py").resolve()
        )
    )

    text = "Incident impacting 2 of 4 lanes; direction: NB"
    lanes_affected, total_lanes, lane_impact, direction = mod.parse_lane_status(text)
    assert lanes_affected == 2
    assert total_lanes == 4
    assert lane_impact in ("partial", "full")
    assert direction in ("NB", "SB", "EB", "WB")


def test_parse_last_update_basic():
    mod = load_module(
        str(
            Path("functions/adt_ingest/fetch_ritis_incidents/__init__.py").resolve()
        )
    )

    ts = mod.parse_last_update("Last updated at 2025-12-01T18:45:00Z")
    assert isinstance(ts, int)
    assert ts > 0
