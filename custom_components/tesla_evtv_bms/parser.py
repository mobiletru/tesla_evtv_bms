"""Parse EVTV LiteCAN UDP packets.

CAN layouts follow the community reference:
https://github.com/wreuvers/tesla_evtv_bms

Extended frames (0x652, 0x654, 0x68F) from mobiletru PRs to the core repo.
Sign convention on 0x150/0x151: positive = discharge, negative = charge.
"""

import logging

_LOGGER = logging.getLogger(__name__)

VALID_CAN_IDS = {0x150, 0x151, 0x650, 0x651, 0x652, 0x654, 0x683, 0x68F}

FAULT_REASONS = {
    0: "No Fault",
    1: "Cell Undervoltage",
    2: "Cell Overvoltage",
    3: "Module Undertemperature",
    4: "Module Overtemperature",
    5: "Voltage Imbalance",
}


def parse_udp_packet(payload: bytes, port: int) -> dict | None:
    _LOGGER.debug(
        "[tesla_evtv_bms] Received UDP payload on port %s: %s (length=%s)",
        port,
        payload.hex(),
        len(payload),
    )

    if len(payload) < 12:
        _LOGGER.warning(
            "[tesla_evtv_bms] Ignored short packet on port %s (length=%s)",
            port,
            len(payload),
        )
        return None

    can_id = payload[8] + (payload[9] << 8) + (payload[10] << 16) + (payload[11] << 24)
    _LOGGER.debug("[tesla_evtv_bms] Parsed CAN ID: %s", hex(can_id))

    if can_id not in VALID_CAN_IDS:
        _LOGGER.debug("[tesla_evtv_bms] Ignored unrecognized CAN ID: %s", hex(can_id))
        return None

    def u16(b0, b1):
        return b0 + (b1 << 8)

    def s16(b0, b1):
        value = b0 + (b1 << 8)
        return value - 0x10000 if value & 0x8000 else value

    def s32(b):
        return int.from_bytes(b, byteorder="little", signed=True)

    result: dict = {}

    if can_id == 0x650:
        result["state_of_charge"] = payload[0] / 2

    elif can_id == 0x651:
        result["lowest_cell"] = u16(payload[0], payload[1]) / 1000
        result["highest_cell"] = u16(payload[2], payload[3]) / 1000
        result["average_cell"] = u16(payload[4], payload[5]) / 1000
        result["max_cells"] = payload[6]
        result["active_cells"] = payload[7]

    elif can_id == 0x151:
        current = s32(payload[0:4]) / 100.0
        power = s32(payload[4:8]) / 100.0
        volts = power / current if current else 0
        result.update(
            {
                "current": round(current, 2),
                "power": round(power),
                "volts": round(volts, 1),
            }
        )

    elif can_id == 0x683:
        result["freq_shift_volts"] = u16(payload[2], payload[3]) / 100
        result["tcch_amps"] = u16(payload[4], payload[5]) / 10

    elif can_id == 0x150:
        raw_current = u16(payload[0], payload[1])
        volts = u16(payload[2], payload[3]) / 10.0

        if raw_current > 32768:
            charging_current = 65535 - raw_current
            current = -float(charging_current)
            power = -round(volts * charging_current)
        else:
            current = float(raw_current)
            power = round(volts * raw_current)

        result.update(
            {
                "current": round(current, 2),
                "power": round(power),
                "volts": round(volts, 1),
                "raw_current": raw_current,
                "pack_ah_used": round(s16(payload[4], payload[5]) / 10.0, 1),
                "highest_temp": payload[6],
                "lowest_temp": payload[7],
            }
        )

    elif can_id == 0x652:
        result["high_voltage_cutoff"] = round(u16(payload[4], payload[5]) / 10.0, 2)
        result["low_voltage_cutoff"] = round(u16(payload[6], payload[7]) / 10.0, 2)

    elif can_id == 0x654:
        status = payload[0]
        result["contactor_negative"] = "Open" if (status & 0x10) else "Closed"
        result["contactor_positive"] = "Open" if (status & 0x20) else "Closed"
        result["charge_enable"] = "On" if (status & 0x04) else "Off"
        result["heat_enable"] = "On" if (status & 0x08) else "Off"
        result["power_source"] = "USB" if (status & 0x40) else "12V"

        fault_code = payload[1] & 0x3F
        result["fault_code"] = fault_code
        result["fault_status"] = FAULT_REASONS.get(fault_code, f"Unknown ({fault_code})")

    elif can_id == 0x68F:
        result["total_modules"] = payload[1]
        result["total_cells"] = payload[1] * 6

    return result