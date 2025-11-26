"""Support for esphome devices."""

from __future__ import annotations

from aioesphomeapi import APIClient
import voluptuous as vol

from homeassistant.components import ffmpeg, websocket_api, zeroconf
from homeassistant.components.bluetooth import async_remove_scanner
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    __version__ as ha_version,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_BLUETOOTH_MAC_ADDRESS, CONF_NOISE_PSK, DATA_FFMPEG_PROXY, DOMAIN
from .dashboard import async_setup as async_setup_dashboard
from .domain_data import DomainData

# Import config flow so that it's added to the registry
from .entry_data import ESPHomeConfigEntry, RuntimeEntryData
from .ffmpeg_proxy import FFmpegProxyData, FFmpegProxyView
from .manager import ESPHomeManager, cleanup_instance

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CLIENT_INFO = f"Home Assistant {ha_version}"

websocket_schema_get_resistive_sensor_config = (
    websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
        {
            vol.Required("type"): "smartvanio/get_resistive_sensor_config_data",
            vol.Required("device_id"): str,
        }
    )
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the esphome component."""
    proxy_data = hass.data[DATA_FFMPEG_PROXY] = FFmpegProxyData()

    await async_setup_dashboard(hass)
    hass.http.register_view(
        FFmpegProxyView(ffmpeg.get_ffmpeg_manager(hass), proxy_data)
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ESPHomeConfigEntry) -> bool:
    """Set up the esphome component."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    password: str | None = entry.data[CONF_PASSWORD]
    noise_psk: str | None = entry.data.get(CONF_NOISE_PSK)

    zeroconf_instance = await zeroconf.async_get_instance(hass)

    cli = APIClient(
        host,
        port,
        password,
        client_info=CLIENT_INFO,
        zeroconf_instance=zeroconf_instance,
        noise_psk=noise_psk,
    )

    domain_data = DomainData.get(hass)
    entry_data = RuntimeEntryData(
        client=cli,
        entry_id=entry.entry_id,
        title=entry.title,
        store=domain_data.get_or_create_store(hass, entry),
        original_options=dict(entry.options),
    )
    entry.runtime_data = entry_data

    manager = ESPHomeManager(
        hass, entry, host, password, cli, zeroconf_instance, domain_data
    )
    await manager.async_start()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ESPHomeConfigEntry) -> bool:
    """Unload an esphome config entry."""
    entry_data = await cleanup_instance(hass, entry)
    return await hass.config_entries.async_unload_platforms(
        entry, entry_data.loaded_platforms
    )


async def async_remove_entry(hass: HomeAssistant, entry: ESPHomeConfigEntry) -> None:
    """Remove an esphome config entry."""
    if bluetooth_mac_address := entry.data.get(CONF_BLUETOOTH_MAC_ADDRESS):
        async_remove_scanner(hass, bluetooth_mac_address.upper())
    await DomainData.get(hass).get_or_create_store(hass, entry).async_remove()


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "smartvanio/get_resistive_sensor_config_data",
        vol.Required("device_id"): str,
    }
)
def websocket_handle_get_resistive_sensor_config(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
):
    """Handle our custom WS command to get config data."""
    # For example, get the config entry from hass.data or by domain
    # This will vary by how you store references to your config entries
    device_id = msg["device_id"]

    config_entry_id = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("device_name") == device_id:
            config_entry_id = entry.entry_id
            break

    if not config_entry_id:
        connection.send_error(msg["id"], "not_found", "Config entry not found.")
        return

    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if not config_entry:
        connection.send_error(msg["id"], "not_found", "Config entry not found.")
        return

    sensor_1_entry = config_entry.options.get(
        "sensor_1", config_entry.data.get("sensor_1", {})
    )
    sensor_2_entry = config_entry.options.get(
        "sensor_2", config_entry.data.get("sensor_2", {})
    )

    response = {
        "sensor_1": {"name": sensor_1_entry.get("name")},
        "sensor_2": {"name": sensor_2_entry.get("name")},
    }

    # Return the data to the caller
    connection.send_result(msg["id"], response)
