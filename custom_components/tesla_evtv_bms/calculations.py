"""Pure calculation functions for Tesla EVTV BMS.

No Home Assistant dependencies — fully unit-testable.

Sign convention (matches CAN 0x150/0x151 parser):
  - Positive current / power => CHARGE (into the pack)
  - Negative current / power => DISCHARGE (out of the pack)
  - current > +1  => "Charging"
  - current < -1  => "Discharging"
  - else          => "Idle"
"""

from typing import Any

from .const import DEFAULT_PACK_SIZE, DEFAULT_CELLS_IN_SERIES

ENERGY_STATE_KEY = "energy_state"
CELLS_PER_MODULE = 6


def resolve_cells_in_series(values: dict[str, Any], config: dict[str, Any]) -> int:
    """Series cell count for pack voltage (S-count).

    Priority:
    1. total_cells from CAN 0x68F (modules × 6) — correct for modules wired in series
    2. total_modules × 6 from CAN 0x68F
    3. User-configured cells_in_series (when not the large-pack default)
    4. active_cells from CAN 0x651 when it looks like a series count (≥ 6)
    5. Config default / active_cells fallback
    """
    total_cells = values.get("total_cells")
    if isinstance(total_cells, (int, float)) and total_cells > 0:
        return int(total_cells)

    total_modules = values.get("total_modules")
    if isinstance(total_modules, (int, float)) and total_modules > 0:
        return int(total_modules) * CELLS_PER_MODULE

    configured = config.get("cells_in_series", DEFAULT_CELLS_IN_SERIES)
    active = values.get("active_cells")

    if configured and configured != DEFAULT_CELLS_IN_SERIES:
        return int(configured)

    if isinstance(active, (int, float)) and active >= CELLS_PER_MODULE:
        return int(active)

    if configured:
        return int(configured)

    if isinstance(active, (int, float)) and active > 0:
        return int(active)

    return DEFAULT_CELLS_IN_SERIES


def derive_volts_and_power(values: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Derive pack voltage and power. Returns only computed keys."""
    derived: dict[str, Any] = {}
    cells_series = resolve_cells_in_series(values, config)
    avg_cell = values.get("average_cell")
    can_volts = values.get("volts")

    derived_volts = None
    if avg_cell is not None and cells_series:
        derived_volts = round(avg_cell * cells_series, 1)

    if isinstance(can_volts, (int, float)) and can_volts > 0:
        # 0x150/0x151 pack voltage is authoritative when cell-derived drifts (e.g. 12S packs).
        if derived_volts is None or abs(derived_volts - can_volts) / can_volts > 0.12:
            derived["volts"] = round(can_volts, 1)
        else:
            derived["volts"] = derived_volts
    elif derived_volts is not None:
        derived["volts"] = derived_volts

    current = values.get("current")
    volts = derived.get("volts", can_volts)
    if current is not None and volts is not None:
        derived["power"] = round(volts * current)
    return derived


def get_battery_status(current: float | None) -> str:
    if current is None:
        return ""
    if current > 1:
        return "Charging"
    if current < -1:
        return "Discharging"
    return "Idle"


def split_charge_discharge(power: float | None) -> tuple[float, float]:
    if power is None:
        return 0.0, 0.0
    if power > 0:
        return 0.0, power
    if power < 0:
        return abs(power), 0.0
    return 0.0, 0.0


def compute_available_energy(soc: float | None, pack_size: float) -> float | None:
    if soc is None:
        return None
    return round(pack_size * soc / 100, 2)


def compute_cell_difference(values: dict[str, Any]) -> float | None:
    if all(k in values for k in ("highest_cell", "lowest_cell")):
        return round(values["highest_cell"] - values["lowest_cell"], 4)
    return None


def compute_trigger_cell_voltage(values: dict[str, Any], soc: float | None) -> float | None:
    if soc is None:
        return None
    if soc >= 75 and "highest_cell" in values:
        return values["highest_cell"]
    if soc <= 25 and "lowest_cell" in values:
        return values["lowest_cell"]
    if "average_cell" in values:
        return values["average_cell"]
    return None


def accumulate_energy(
    power: float | None,
    delta_seconds: float,
    prev_charge: float = 0.0,
    prev_discharge: float = 0.0,
) -> dict[str, float | str | None]:
    charge = prev_charge
    discharge = prev_discharge
    increment = 0.0
    flow = None
    if power is not None and delta_seconds > 0:
        increment = (abs(power) * delta_seconds / 3600) / 1000
        if power > 0:
            charge += increment
            flow = "charge"
        elif power < 0:
            discharge += increment
            flow = "discharge"
    return {
        "charge": charge,
        "discharge": discharge,
        "increment": increment,
        "flow": flow,
    }


def compute_derived_state(
    raw: dict[str, Any],
    config: dict[str, Any],
    *,
    prev_energy: dict[str, float] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    derived = derive_volts_and_power(raw, config)
    view = {**raw, **derived}

    pack_size = config.get("pack_size", DEFAULT_PACK_SIZE)
    soc = view.get("state_of_charge")
    current = view.get("current")
    power = view.get("power")

    if soc is not None:
        derived["available_energy"] = compute_available_energy(soc, pack_size)

    if current is not None:
        derived["battery_status"] = get_battery_status(current)

    if power is not None:
        discharge, charge = split_charge_discharge(power)
        derived["discharge"] = discharge
        derived["charge"] = charge

    cell_diff = compute_cell_difference(view)
    if cell_diff is not None:
        derived["cell_difference"] = cell_diff

    trig = compute_trigger_cell_voltage(view, soc)
    if trig is not None:
        derived["trigger_cell_voltage"] = trig

    if prev_energy is not None and now is not None and power is not None:
        last = prev_energy.get("last_update", now)
        delta = max(0.0, now - last)
        energy = accumulate_energy(
            power,
            delta,
            prev_energy.get("charge", 0.0),
            prev_energy.get("discharge", 0.0),
        )
        derived["charge_energy"] = round(energy["charge"], 3)
        derived["discharge_energy"] = round(energy["discharge"], 3)
        derived[ENERGY_STATE_KEY] = {
            "charge": energy["charge"],
            "discharge": energy["discharge"],
            "last_update": now,
            "increment": energy["increment"],
            "flow": energy["flow"],
        }

    return derived


UTILITY_METER_PERIODS = ("hour", "day", "week", "month", "year")


def apply_period_energy_increments(
    values: dict[str, Any],
    energy_state: dict[str, Any],
    periods: tuple[str, ...] = UTILITY_METER_PERIODS,
) -> None:
    """Add this tick's kWh increment to hour/day/week/month/year accumulators."""
    flow = energy_state.get("flow")
    increment = energy_state.get("increment", 0.0)
    if not flow or not increment:
        return
    base = "discharge_energy" if flow == "discharge" else "charge_energy"
    for label in periods:
        meter_key = f"{base}_{label}"
        values[meter_key] = round(values.get(meter_key, 0.0) + increment, 3)


def apply_derived_state(
    values: dict[str, Any],
    derived: dict[str, Any],
    coordinator_energy: dict[str, float] | None = None,
) -> None:
    for key, val in derived.items():
        if key == ENERGY_STATE_KEY:
            continue
        values[key] = val

    energy_state = derived.get(ENERGY_STATE_KEY)
    if energy_state and coordinator_energy is not None:
        coordinator_energy["charge"] = energy_state["charge"]
        coordinator_energy["discharge"] = energy_state["discharge"]
        coordinator_energy["last_update"] = energy_state["last_update"]
        apply_period_energy_increments(values, energy_state)


def update_rolling_samples(samples: list[float], new_power: float | None, window: int) -> list[float]:
    if new_power is None:
        return list(samples)
    new_samples = list(samples) + [new_power]
    if len(new_samples) > window:
        new_samples = new_samples[-window:]
    return new_samples


def compute_rolling_average(samples: list[float]) -> float | None:
    if not samples:
        return None
    return round(sum(samples) / len(samples), 1)


def compute_hours_to(
    avg_power: float | None,
    status: str,
    available_energy: float,
    pack_size: float,
) -> dict[str, float]:
    hours_empty = 0.0
    hours_full = 0.0
    if avg_power is not None and abs(avg_power) > 0:
        rate_kw = abs(avg_power) / 1000.0
        if status == "Charging":
            hours_full = round((pack_size - available_energy) / rate_kw, 2)
        elif status == "Discharging":
            hours_empty = round(available_energy / rate_kw, 2)
    return {"hours_to_empty": hours_empty, "hours_to_full": hours_full}


def compute_summary(status: str, hours_to_empty: float, hours_to_full: float) -> str:
    if status == "Discharging":
        hrs = hours_to_empty
        hrs_str = f"{hrs:.1f}" if hrs < 10 else f"{int(hrs)}"
        return f"{hrs_str} hrs to Empty"
    if status == "Charging":
        hrs = hours_to_full
        hrs_str = f"{hrs:.1f}" if hrs < 10 else f"{int(hrs)}"
        return f"{hrs_str} hrs to Full"
    return "Idle"