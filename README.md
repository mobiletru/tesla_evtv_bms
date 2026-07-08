# Tesla EVTV BMS

Home Assistant integration for the EVTV Tesla BMS controller. Listens on a UDP port and decodes CAN data into sensors.

## Features

- Pack name, port, and pack configuration via UI
- Real-time UDP listener
- Sensors for voltage, current, SoC, power, cell stats, temperatures, charge/discharge
- Utility meters for charge and discharge by hour, day, week, month, and year
- Pure calculation module for testable derivation logic

## Installation (HACS)

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/mobiletru/tesla_evtv_bms` as type **Integration**
3. Install and restart Home Assistant
4. Settings → Devices & Services → **+** → Tesla EVTV BMS

## Development

```bash
python test_voltage_calc.py
./scripts/push.sh
```