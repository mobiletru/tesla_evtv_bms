# Tesla EVTV BMS + SMA Sunny WebBox

Combined Home Assistant integration: listens on UDP for an **EVTV CAN-DUE v2 / LiteCAN**
broadcast and decodes it into BMS sensors, and (optionally) polls an **SMA Sunny WebBox**
on the same network for solar sensors. One config entry, one device tree, one app.

Fork of the community integration at [wreuvers/tesla_evtv_bms](https://github.com/wreuvers/tesla_evtv_bms), extended for multi-module Tesla packs, additional CAN frames, unknown-frame fallback sensors, WebBox polling, and fixed utility-meter accumulation. Current sign: **positive = discharging**, **negative = charging** (EVTV LiteCAN display convention). Example: 125 A discharge reads **+125 A**.

## Features

- Pack name, port, and pack configuration via UI
- Real-time UDP listener for the CAN broadcast (default port 6850 — set to whatever
  your CAN-DUE v2 actually targets, e.g. `6550`)
- Sensors for voltage, current, SoC, power, cell stats, temperatures, contactors, faults
- **Every CAN ID on the bus becomes a sensor.** IDs with a known layout (table below) get
  named, scaled fields; anything else still shows up as `can_<id>_raw` (full hex payload)
  and `can_<id>_u16` (first two bytes as a graphable number) instead of being dropped
  silently — see `dashboards/debug_dashboard.yaml` for reverse-engineering these.
- Optional SMA Sunny WebBox polling (`home.ajax`, no auth) for live solar power / daily
  yield / total yield, as its own device linked to the pack. RPC (parameter-level data,
  MD5-hashed password) is attempted best-effort and ignored if the WebBox has RPC
  disabled in its security settings (the out-of-the-box default).
- Charge/discharge energy totals plus hour/day/week/month/year utility meters
- Pack voltage derived from average cell × active cells (reliable on multi-module packs)
- Pure `calculations.py` / `webbox.py` modules for testable logic, no HA dependency

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
| anything else | `can_<id>_raw` + `can_<id>_u16` (unnamed, unscaled fallback) |

On one live pack this surfaced `0x653`, `0x655`-`0x65a` (updating ~1/sec, looks like
per-module telemetry) and `0x680`-`0x687` (low-frequency, looks event-driven) — none of
these have a confirmed decode yet.

## Installation (HACS)

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/mobiletru/tesla_evtv_bms` as type **Integration**
3. Install and restart Home Assistant
4. Settings → Devices & Services → **+** → Tesla EVTV BMS
5. Fill in the CAN listener port and pack config. Leave **WebBox host** blank to skip
   solar sensors, or set it to your WebBox's IP (e.g. `192.168.100.180`) plus its
   access password if you've set one.
6. Import `dashboards/debug_dashboard.yaml` as a new dashboard (Settings → Dashboards →
   **+ Add Dashboard** → *New dashboard from YAML*) and replace `EVTV_NAME` throughout
   with your pack's slugified device name — see the comment at the top of that file.

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