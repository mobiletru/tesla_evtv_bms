"""Tests for pure calculations module.

Run: python test_voltage_calc.py
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

_calc = importlib.import_module("tesla_evtv_bms.calculations")

ENERGY_STATE_KEY = _calc.ENERGY_STATE_KEY
accumulate_energy = _calc.accumulate_energy
apply_derived_state = _calc.apply_derived_state
compute_cell_difference = _calc.compute_cell_difference
compute_derived_state = _calc.compute_derived_state
compute_hours_to = _calc.compute_hours_to
compute_rolling_average = _calc.compute_rolling_average
compute_summary = _calc.compute_summary
compute_trigger_cell_voltage = _calc.compute_trigger_cell_voltage
derive_volts_and_power = _calc.derive_volts_and_power
get_battery_status = _calc.get_battery_status
split_charge_discharge = _calc.split_charge_discharge
update_rolling_samples = _calc.update_rolling_samples


def test_pack_metrics_from_cells():
    res = derive_volts_and_power(
        {"average_cell": 3.805, "active_cells": 216, "current": 30},
        {"cells_in_series": 96},
    )
    assert res == {"volts": 821.9, "power": 24657}


def test_sign_convention_and_status():
    assert get_battery_status(30) == "Discharging"
    assert get_battery_status(-30) == "Charging"
    assert get_battery_status(0) == "Idle"
    assert split_charge_discharge(100) == (100.0, 0.0)
    assert split_charge_discharge(-50) == (0.0, 50.0)


def test_energy_accumulation():
    e = accumulate_energy(100, 3600, 0.0, 0.0)
    assert e["discharge"] == 0.1
    e2 = accumulate_energy(-200, 1800, 1.0, 0.5)
    assert round(e2["charge"], 3) == 1.1


def test_compute_derived_state_integration():
    raw = {
        "state_of_charge": 50,
        "current": 30,
        "average_cell": 3.805,
        "active_cells": 216,
        "highest_cell": 3.9,
        "lowest_cell": 3.7,
    }
    config = {"pack_size": 75.0, "cells_in_series": 96}
    prev_energy = {"charge": 0.0, "discharge": 0.0, "last_update": 1000.0}

    derived = compute_derived_state(raw, config, prev_energy=prev_energy, now=4600.0)
    assert derived["discharge_energy"] == 24.657
    assert ENERGY_STATE_KEY in derived

    values = dict(raw)
    energy = dict(prev_energy)
    apply_derived_state(values, derived, energy)
    assert values["power"] == 24657
    assert energy["last_update"] == 4600.0


if __name__ == "__main__":
    test_pack_metrics_from_cells()
    test_sign_convention_and_status()
    test_energy_accumulation()
    test_compute_derived_state_integration()
    print("test_voltage_calc.py: ok")