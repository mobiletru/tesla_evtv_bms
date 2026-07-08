DOMAIN = "tesla_evtv_bms"
PLATFORMS = ["sensor"]

CONF_NAME = "name"
CONF_PORT = "port"

SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_{{}}_update"

DEFAULT_PORT = 6850
DEFAULT_PACK_SIZE = 75.0
DEFAULT_CELLS_IN_SERIES = 96
DEFAULT_MIN_CELL_VOLTS = 3.2
DEFAULT_MAX_CELL_VOLTS = 4.1


def pack_config_from_data(data: dict) -> dict:
    """Build runtime pack config from a config entry data dict."""
    return {
        "pack_size": data.get("pack_size", DEFAULT_PACK_SIZE),
        "cells_in_series": data.get("cells_in_series", DEFAULT_CELLS_IN_SERIES),
        "min_cell_volts": data.get("min_cell_volts", DEFAULT_MIN_CELL_VOLTS),
        "max_cell_volts": data.get("max_cell_volts", DEFAULT_MAX_CELL_VOLTS),
    }