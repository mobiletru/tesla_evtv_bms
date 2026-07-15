import asyncio
import socket
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_WEBBOX_HOST,
    CONF_WEBBOX_PASSWORD,
    CONF_WEBBOX_SCAN_INTERVAL,
    DEFAULT_WEBBOX_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SIGNAL_UPDATE_ENTITY,
    pack_config_from_data,
)
from .parser import parse_udp_packet
from .webbox import async_poll_webbox

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    name = entry.data["name"]
    port = entry.data["port"]
    name_lower = name.lower()

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][name_lower] = {
        "entities": {},
        "values": {},
        "config": pack_config_from_data(entry.data),
    }

    def udp_callback(sock):
        try:
            data, _ = sock.recvfrom(1024)
            parsed = parse_udp_packet(data, port)
            if parsed:
                name_data = hass.data[DOMAIN][name_lower]
                previous_values = name_data.get("values", {})
                merged_values = {**previous_values, **parsed}

                async_dispatcher_send(
                    hass,
                    SIGNAL_UPDATE_ENTITY.format(name_lower),
                    merged_values,
                )
        except BlockingIOError:
            pass
        except Exception as e:
            _LOGGER.error("[%s] UDP read error on %s: %s", DOMAIN, name, e)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", port))
        sock.setblocking(False)
        loop = asyncio.get_event_loop()
        loop.add_reader(sock, udp_callback, sock)
        _LOGGER.info("Started non-blocking UDP listener for %s on port %d", name, port)
    except OSError as e:
        _LOGGER.error("Failed to bind UDP socket on port %d for %s: %s", port, name, e)
        return False

    webbox_host = entry.data.get(CONF_WEBBOX_HOST, "").strip()
    if webbox_host:
        session = async_get_clientsession(hass)
        webbox_password = entry.data.get(CONF_WEBBOX_PASSWORD) or None
        scan_interval = entry.data.get(CONF_WEBBOX_SCAN_INTERVAL, DEFAULT_WEBBOX_SCAN_INTERVAL)

        async def poll_webbox(now=None):
            try:
                values = await async_poll_webbox(session, webbox_host, webbox_password)
            except Exception as e:
                _LOGGER.warning("[%s] WebBox poll failed (%s): %s", DOMAIN, webbox_host, e)
                return
            if values:
                previous_values = hass.data[DOMAIN][name_lower].get("values", {})
                async_dispatcher_send(
                    hass,
                    SIGNAL_UPDATE_ENTITY.format(name_lower),
                    {**previous_values, **values},
                )

        entry.async_on_unload(
            async_track_time_interval(hass, poll_webbox, timedelta(seconds=scan_interval))
        )
        hass.async_create_task(poll_webbox())
        _LOGGER.info("Started WebBox poller for %s at %s every %ds", name, webbox_host, scan_interval)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True