"""The bemfa integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_UID, DOMAIN, OPTIONS_CONFIG

_LOGGING = logging.getLogger(__name__)


def _import_setup_dependencies():
    """Import modules that register sync types and pull external requirements."""
    from . import (  # noqa: F401
        sync_binary_sensor,
        sync_sensor,
        sync_light,
        sync_fan,
        sync_cover,
        sync_climate,
        sync_switch,
    )
    from .service import BemfaService

    return BemfaService


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up bemfa from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    BemfaService = await hass.async_add_executor_job(_import_setup_dependencies)
    service = BemfaService(hass, entry.data[CONF_UID])
    await service.async_start(
        entry.options[OPTIONS_CONFIG] if OPTIONS_CONFIG in entry.options else {}
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "service": service,
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data is not None:
        data["service"].stop()
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
