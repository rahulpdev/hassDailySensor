"""The Day of Month Sensor integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__name__)

# List of platforms to support.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Day of Month Sensor from a config entry.
    
    This function initializes the integration, stores configuration data,
    and sets up the sensor platform.
    
    Args:
        hass: The Home Assistant instance.
        entry: The configuration entry containing user-provided settings.
        
    Returns:
        bool: True if setup was successful, False otherwise.
    """
    # Store configuration data in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the configuration entry to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.
    
    This function removes the integration and cleans up any entities
    that were created.
    
    Args:
        hass: The Home Assistant instance.
        entry: The configuration entry to unload.
        
    Returns:
        bool: True if unload was successful, False otherwise.
    """
    # Unload the sensor platform
    unload_ok: bool = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    
    # Remove configuration data if unload was successful
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
