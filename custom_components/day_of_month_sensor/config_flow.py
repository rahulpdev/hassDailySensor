"""Config flow for Day of Month Sensor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry

from .const import (
    DOMAIN,
    CONF_ENTITY_ID,
    CONF_TRACK_VALUE,
    CONF_AGGREGATION,
    CONF_HISTORIC_RANGE,
    CONF_UPDATE_FREQUENCY,
    TRACK_VALUE_OPTIONS,
    AGGREGATION_OPTIONS,
    HISTORIC_RANGE_OPTIONS,
    UPDATE_FREQUENCY_OPTIONS,
    VALID_STATE_CLASSES,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def validate_entity_id(
    hass: HomeAssistant, entity_id: str
) -> tuple[bool, str | None]:
    """Validate that the entity ID is a numeric sensor with a valid state class.
    
    This function checks if the entity exists, is a sensor, has a valid state class,
    and has a numeric state value.
    
    Args:
        hass: The Home Assistant instance.
        entity_id: The entity ID to validate.
        
    Returns:
        tuple[bool, str | None]: A tuple containing:
            - bool: True if the entity is valid, False otherwise.
            - str | None: Error message if validation failed, None otherwise.
    """
    entity_registry: EntityRegistry = er.async_get(hass)
    entity_entry: RegistryEntry | None = entity_registry.async_get(entity_id)
    
    if not entity_entry:
        return False, "Entity not found"
    
    if not entity_entry.domain == SENSOR_DOMAIN:
        return False, "Entity is not a sensor"
    
    # Check if the entity has a valid state class
    state: State | None = hass.states.get(entity_id)
    if not state:
        return False, "Entity state not available"
    
    state_class: str | None = state.attributes.get("state_class")
    if not state_class or state_class not in VALID_STATE_CLASSES:
        return False, (
            f"Entity must have one of these state classes: "
            f"{', '.join(VALID_STATE_CLASSES)}"
        )
    
    # Check if the entity has a numeric state
    try:
        float(state.state)
    except (ValueError, TypeError):
        return False, "Entity must have a numeric state"
    
    return True, None


class DayOfMonthSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Day of Month Sensor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step of the config flow.
        
        This method presents a form to the user for configuring the integration
        and validates the user's input.
        
        Args:
            user_input: Dictionary containing user input if the form was submitted,
                        None otherwise.
                        
        Returns:
            FlowResult: The result of the config flow step.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id: str = user_input[CONF_ENTITY_ID]
            
            # Check if this entity is already configured
            await self.async_set_unique_id(entity_id)
            self._abort_if_unique_id_configured()
            
            # Validate the entity
            is_valid, error_msg = await validate_entity_id(
                self.hass, entity_id
            )
            if not is_valid:
                errors["entity_id"] = "invalid_entity"
                _LOGGER.error("Entity validation failed: %s", error_msg)
            else:
                # All validation passed, create the config entry
                return self.async_create_entry(
                    title=f"Day of Month Sensor for {entity_id}",
                    data=user_input,
                )

        # Get the entity registry
        er.async_get(self.hass)

        # Build the schema
        schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        filter={"domain": SENSOR_DOMAIN},
                        multiple=False,
                    ),
                ),
                vol.Required(CONF_TRACK_VALUE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=TRACK_VALUE_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required(CONF_AGGREGATION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=AGGREGATION_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required(CONF_HISTORIC_RANGE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=HISTORIC_RANGE_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required(CONF_UPDATE_FREQUENCY): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=UPDATE_FREQUENCY_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
