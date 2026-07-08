"""Parser tests aligned with wreuvers/tesla_evtv_bms CAN layouts."""

import importlib
import sys
import types
from pathlib import Path

_pkg_root = Path(__file__).parent / "custom_components"
sys.path.insert(0, str(_pkg_root))
_pkg = types.ModuleType("tesla_evtv_bms")
_pkg.__path__ = [str(_pkg_root / "tesla_evtv_bms")]
sys.modules["tesla_evtv_bms"] = _pkg

_parser = importlib.import_module("tesla_evtv_bms.parser")
parse_udp_packet = _parser.parse_udp_packet


def _frame(can_id: int, data: bytes) -> bytes:
    assert len(data) == 8
    return data + can_id.to_bytes(4, byteorder="little")


def test_soc_0x650():
    parsed = parse_udp_packet(_frame(0x650, bytes([170, 0, 0, 0, 0, 0, 0, 0])), 6850)
    assert parsed["state_of_charge"] == 85.0


def test_pack_0x150_discharge_sign():
    # raw_current=100 A discharge => negative current (out of pack)
    parsed = parse_udp_packet(_frame(0x150, bytes([0x64, 0x00, 0xA0, 0x0F, 0, 0, 25, 20])), 6850)
    assert parsed["current"] == -100.0
    assert parsed["power"] == -40000


def test_pack_0x150_charge_sign():
    # raw_current=65436 => 99 A charge => positive current (into pack)
    parsed = parse_udp_packet(_frame(0x150, bytes([0x9C, 0xFF, 0xA0, 0x0F, 0, 0, 25, 20])), 6850)
    assert parsed["current"] == 99.0
    assert parsed["power"] == 39600
    assert parsed["highest_temp"] == 25
    assert parsed["lowest_temp"] == 20


def test_fault_0x654():
    parsed = parse_udp_packet(_frame(0x654, bytes([0x00, 0x00, 0, 0, 0, 0, 0, 0])), 6850)
    assert parsed["fault_status"] == "No Fault"
    assert parsed["power_source"] == "12V"


if __name__ == "__main__":
    test_soc_0x650()
    test_pack_0x150_discharge_sign()
    test_pack_0x150_charge_sign()
    test_fault_0x654()
    print("test_parser.py: ok")