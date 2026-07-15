"""Tests for the SMA Sunny WebBox poller helpers.

Fixture values are taken from a live WebBox (home.ajax) and from the
official RPC manual's example response (SWebBoxRPC-BA-de-14).
"""

import importlib
import sys
import types
from pathlib import Path

_pkg_root = Path(__file__).parent / "custom_components"
sys.path.insert(0, str(_pkg_root))
_pkg = types.ModuleType("tesla_evtv_bms")
_pkg.__path__ = [str(_pkg_root / "tesla_evtv_bms")]
sys.modules["tesla_evtv_bms"] = _pkg

_webbox = importlib.import_module("tesla_evtv_bms.webbox")
parse_overview_ajax = _webbox.parse_overview_ajax
parse_rpc_plant_overview = _webbox.parse_rpc_plant_overview
webbox_password_hash = _webbox.webbox_password_hash
build_rpc_request = _webbox.build_rpc_request


def test_parse_home_ajax_live_sample():
    payload = {
        "Items": [
            {"Power": "-900 W"},
            {"DailyYield": "8.2 kWh"},
            {"TotalYield": "5348.2 kWh"},
        ]
    }
    assert parse_overview_ajax(payload) == {
        "webbox_power": -900.0,
        "webbox_daily_yield": 8.2,
        "webbox_total_yield": 5348.2,
    }


def test_parse_home_ajax_ignores_unknown_keys():
    assert parse_overview_ajax({"Items": [{"SomethingElse": "1 X"}]}) == {}


def test_parse_home_ajax_ignores_unparseable_value():
    assert parse_overview_ajax({"Items": [{"Power": "n/a"}]}) == {}


def test_parse_rpc_plant_overview_manual_example():
    body = """
    {
        "version": "1.0",
        "proc": "GetPlantOverview",
        "id": "1",
        "result": {
            "overview": [
                {"meta": "GriPwr", "name": "Momentanleistung", "value": "4250", "unit": "W"},
                {"meta": "GriEgyTdy", "name": "Tagesenergie", "value": "45.23", "unit": "kWh"}
            ]
        }
    }
    """
    assert parse_rpc_plant_overview(body) == {
        "webbox_rpc_gripwr": 4250.0,
        "webbox_rpc_griegytdy": 45.23,
    }


def test_parse_rpc_plant_overview_disabled_device_returns_none():
    """When RPC is disabled the WebBox echoes its default HTML frameset instead of JSON."""
    html = "<!DOCTYPE html PUBLIC \"-//W3C//DTD HTML 4.01 Frameset//EN\">\n<html></html>"
    assert parse_rpc_plant_overview(html) is None


def test_password_hash_is_md5():
    # Matches the worked example in SMA's RPC manual (SWebBoxRPC-BA-de-14), which also
    # hashes the password "sma" to this value.
    assert webbox_password_hash("sma") == "a289fa4252ed5af8e3e9f9bee545c172"


def test_build_rpc_request_omits_passwd_when_not_given():
    req = build_rpc_request("GetPlantOverview")
    assert "passwd" not in req
    assert req["proc"] == "GetPlantOverview"
    assert req["format"] == "JSON"


def test_build_rpc_request_includes_hashed_passwd():
    req = build_rpc_request("GetDevices", password="sma")
    assert req["passwd"] == webbox_password_hash("sma")


if __name__ == "__main__":
    test_parse_home_ajax_live_sample()
    test_parse_home_ajax_ignores_unknown_keys()
    test_parse_home_ajax_ignores_unparseable_value()
    test_parse_rpc_plant_overview_manual_example()
    test_parse_rpc_plant_overview_disabled_device_returns_none()
    test_password_hash_is_md5()
    test_build_rpc_request_omits_passwd_when_not_given()
    test_build_rpc_request_includes_hashed_passwd()
    print("test_webbox.py: ok")
