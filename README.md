# Tesla EVTV BMS

Home Assistant integration for the EVTV Tesla BMS controller. Listens on a UDP port and decodes CAN data into sensors.

Fork of the community integration at [wreuvers/tesla_evtv_bms](https://github.com/wreuvers/tesla_evtv_bms), extended for multi-module Tesla packs, additional CAN frames, and fixed utility-meter accumulation. Current sign: **positive = charging**, **negative = discharging** (matches upstream CAN layout).

## Features

- Pack name, port, and pack configuration via UI
- Real-time UDP listener
- Sensors for voltage, current, SoC, power, cell stats, temperatures, contactors, faults
- Charge/discharge energy totals plus hour/day/week/month/year utility meters
- Pack voltage derived from average cell × active cells (reliable on multi-module packs)
- Pure `calculations.py` module for testable derivation logic

### CAN frames (from core + extended PRs)

| CAN ID | Sensors |
|--------|---------|
| `0x650` | state_of_charge |
| `0x651` | lowest/highest/average cell, max/active cells |
| `0x150` | current, power, temps, pack_ah_used |
| `0x151` | alternate current/power/volts frame |
| `0x652` | high/low voltage cutoff |
| `0x654` | contactors, charge/heat enable, power source, fault status |
| `0x683` | freq_shift_volts, tcch_amps |
| `0x68F` | total_modules, total_cells |

## Installation (HACS)

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/mobiletru/tesla_evtv_bms` as type **Integration**
3. Install and restart Home Assistant
4. Settings → Devices & Services → **+** → Tesla EVTV BMS

## Upstream

- Core repo: https://github.com/wreuvers/tesla_evtv_bms
- Report upstream bugs there when they apply to the base integration
- This fork keeps mobiletru-specific fixes and extensions

## Development

```bash
python test_voltage_calc.py
./scripts/push.sh
```

Add upstream for comparison:

```bash
git remote add upstream https://github.com/wreuvers/tesla_evtv_bms.git
git fetch upstream
```