"""Platform for Day of Month Sensor integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import statistics
from typing import Any, Callable

from homeassistant.components.recorder.statistics import (
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENTITY_ID,
    CONF_TRACK_VALUE,
    CONF_AGGREGATION,
    CONF_HISTORIC_RANGE,
    CONF_UPDATE_FREQUENCY,
    TRACK_VALUE_MEAN,
    TRACK_VALUE_MIN,
    TRACK_VALUE_MAX,
    TRACK_VALUE_STATE,
    AGGREGATION_MAXIMUM,
    AGGREGATION_MINIMUM,
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN,
    AGGREGATION_STD_DEV,
    HISTORIC_RANGE_ANNUAL,
    HISTORIC_RANGE_MONTHLY,
    UPDATE_FREQUENCY_HOURLY,
    UPDATE_FREQUENCY_DAILY,
    ATTR_TRACK_VALUE,
    ATTR_AGGREGATION,
    ATTR_HISTORIC_RANGE,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Day of Month Sensor platform.
    
    This function creates and adds sensor entities based on the configuration entry.
    
    Args:
        hass: The Home Assistant instance.
        config_entry: The configuration entry containing user-provided settings.
        async_add_entities: Callback to add new entities to Home Assistant.
        
    Returns:
        None
    """
    # Get the configuration from the entry
    entity_id: str = config_entry.data[CONF_ENTITY_ID]
    track_value: str = config_entry.data[CONF_TRACK_VALUE]
    aggregation: str = config_entry.data[CONF_AGGREGATION]
    historic_range: str = config_entry.data[CONF_HISTORIC_RANGE]
    update_frequency: str = config_entry.data[CONF_UPDATE_FREQUENCY]

    # Create and add the sensor entity
    async_add_entities(
        [
            DayOfMonthSensor(
                hass,
                config_entry.entry_id,
                entity_id,
                track_value,
                aggregation,
                historic_range,
                update_frequency,
            )
        ],
        True,
    )


class DayOfMonthSensor(SensorEntity, RestoreEntity):
    """Representation of a Day of Month Sensor."""

    _attr_should_poll: bool = False
    _attr_state_class: SensorStateClass = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        entity_id: str,
        track_value: str,
        aggregation: str,
        historic_range: str,
        update_frequency: str,
    ) -> None:
        """Initialize the Day of Month Sensor.
        
        Args:
            hass: The Home Assistant instance.
            entry_id: The config entry ID.
            entity_id: The source entity ID to track.
            track_value: The value to track (mean, min, max, state).
            aggregation: The aggregation method to use.
            historic_range: The historic range to consider (annual, monthly).
            update_frequency: How often to update (hourly, daily).
            
        Returns:
            None
        """
        self.hass: HomeAssistant = hass
        self._entry_id: str = entry_id
        self._entity_id: str = entity_id
        self._track_value: str = track_value
        self._aggregation: str = aggregation
        self._historic_range: str = historic_range
        self._update_frequency: str = update_frequency
        
        # Set up entity attributes
        entity_name: str = entity_id.split('.')[-1]
        self._attr_name: str = f"Day of Month {aggregation.capitalize()} of {entity_name}"
        self._attr_unique_id: str = f"{entry_id}_{entity_id}"
        self._attr_extra_state_attributes: dict[str, str] = {
            ATTR_TRACK_VALUE: track_value,
            ATTR_AGGREGATION: aggregation,
            ATTR_HISTORIC_RANGE: historic_range,
        }
        
        # Will be set in async_added_to_hass
        self._remove_update_listener: Callable[[], None] | None = None
        self._attr_native_value: float | str | None = None
        self._attr_native_unit_of_measurement: str | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added.
        
        This method is called when the entity is added to Home Assistant.
        It restores the previous state if available, sets up the update interval,
        and performs an initial update.
        
        Args:
            None
            
        Returns:
            None
        """
        await super().async_added_to_hass()
        
        # Restore previous state if available
        if (state := await self.async_get_last_state()) is not None:
            self._attr_native_value = state.state
            
            # Restore attributes
            if ATTR_UNIT_OF_MEASUREMENT in state.attributes:
                self._attr_native_unit_of_measurement = state.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
        
        # Get the unit of measurement from the source entity
        source_state: State | None = self.hass.states.get(self._entity_id)
        if source_state and ATTR_UNIT_OF_MEASUREMENT in source_state.attributes:
            self._attr_native_unit_of_measurement = source_state.attributes[
                ATTR_UNIT_OF_MEASUREMENT
            ]
        
        # Set up update interval based on configuration
        if self._update_frequency == UPDATE_FREQUENCY_HOURLY:
            # Update every hour at the beginning of the hour
            self._remove_update_listener = async_track_time_interval(
                self.hass,
                self._async_update,
                timedelta(hours=1),
                cancel_on_shutdown=True,
            )
        else:  # UPDATE_FREQUENCY_DAILY
            # Update once a day at midnight
            self._remove_update_listener = async_track_time_interval(
                self.hass,
                self._async_update,
                timedelta(days=1),
                cancel_on_shutdown=True,
            )
        
        # Do an initial update
        await self._async_update(None)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass.
        
        This method is called when the entity is about to be removed from
        Home Assistant. It cancels any scheduled updates.
        
        Args:
            None
            
        Returns:
            None
        """
        if self._remove_update_listener:
            self._remove_update_listener()

    async def _async_update(self, _now: datetime | None = None) -> None:
        """Update the sensor state.
        
        This method fetches statistics for the source entity, filters them based
        on the historic range, extracts the values to track, and calculates the
        aggregation.
        
        Args:
            _now: The current datetime, provided by the scheduler.
                 Can be None for manual updates.
                 
        Returns:
            None
        """
        # Get the current date
        now: datetime = dt_util.now()
        
        # Get statistics for the entity
        try:
            if self._update_frequency == UPDATE_FREQUENCY_DAILY:
                # For daily updates, we only want the last value for each day
                _LOGGER.warning("Fetching daily statistics for entity: %s", self._entity_id)
                stats: list[dict[str, Any]] = await self.hass.async_add_executor_job(
                    get_last_statistics,
                    self.hass,
                    1,  # Get the most recent statistic
                    self._entity_id,
                    True,  # Include the current day
                )
                _LOGGER.warning("Retrieved %d daily statistics records", len(stats))
            else:
                # For hourly updates, get all statistics
                _LOGGER.warning(
                    "Fetching hourly statistics for entity: %s (last 365 days)",
                    self._entity_id
                )
                start_time = dt_util.as_utc(
                    dt_util.start_of_local_day(now - timedelta(days=365))
                )
                _LOGGER.warning("Start time for statistics: %s", start_time)
                
                stats_result: dict[str, list[dict[str, Any]]] = await self.hass.async_add_executor_job(
                    statistics_during_period,
                    self.hass,
                    start_time,
                    None,  # No end time (up to now)
                    [self._entity_id],
                    "hour",  # Hourly statistics
                    None,  # No units conversion
                    {"sum", "mean", "min", "max", "state"},  # All statistic types
                )
                stats = stats_result.get(self._entity_id, [])
                _LOGGER.warning("Retrieved %d hourly statistics records", len(stats))
                
                # Log a sample of the statistics data
                if stats:
                    sample = stats[0]
                    _LOGGER.warning(
                        "Sample statistic record: start=%s, fields=%s",
                        sample.get("start"),
                        {k: v for k, v in sample.items() if k != "start"}
                    )
        except Exception as ex:
            _LOGGER.error("Error getting statistics: %s", ex)
            self._attr_native_value = None
            self.async_write_ha_state()
            return
        
        # Filter statistics based on historic range
        filtered_stats: list[dict[str, Any]] = []
        _LOGGER.warning(
            "Filtering statistics for historic range: %s (current day: %d, month: %d)",
            self._historic_range,
            now.day,
            now.month
        )
        
        for stat in stats:
            stat_datetime: datetime = dt_util.as_local(stat["start"])
            
            if self._historic_range == HISTORIC_RANGE_ANNUAL:
                # Match day and month
                if stat_datetime.day == now.day and stat_datetime.month == now.month:
                    filtered_stats.append(stat)
            else:  # HISTORIC_RANGE_MONTHLY
                # Match day only
                if stat_datetime.day == now.day:
                    filtered_stats.append(stat)
        
        _LOGGER.warning(
            "After filtering, found %d matching records for day %d",
            len(filtered_stats),
            now.day
        )
        
        # Log some sample dates from filtered stats
        if filtered_stats:
            sample_dates = [
                dt_util.as_local(stat["start"]).strftime("%Y-%m-%d %H:%M")
                for stat in filtered_stats[:3]
            ]
            _LOGGER.warning("Sample dates from filtered stats: %s", sample_dates)
        
        # Extract the values to track
        values: list[float] = []
        _LOGGER.warning("Extracting '%s' values from filtered statistics", self._track_value)
        
        for stat in filtered_stats:
            if self._track_value == TRACK_VALUE_MEAN and "mean" in stat:
                values.append(stat["mean"])
            elif self._track_value == TRACK_VALUE_MIN and "min" in stat:
                values.append(stat["min"])
            elif self._track_value == TRACK_VALUE_MAX and "max" in stat:
                values.append(stat["max"])
            elif self._track_value == TRACK_VALUE_STATE and "state" in stat:
                values.append(stat["state"])
        
        _LOGGER.warning("Extracted %d values for '%s'", len(values), self._track_value)
        
        # Log the extracted values
        if values:
            _LOGGER.warning(
                "Sample values (up to 5): %s", 
                [round(v, 2) if isinstance(v, float) else v for v in values[:5]]
            )
        
        # Calculate the aggregation
        _LOGGER.warning("Calculating '%s' aggregation on %d values", self._aggregation, len(values))
        
        if not values:
            _LOGGER.warning("No historical data found for %s", self._entity_id)
            self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MAXIMUM:
            try:
                self._attr_native_value = max(values)
                _LOGGER.warning("Maximum value calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating maximum: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MINIMUM:
            try:
                self._attr_native_value = min(values)
                _LOGGER.warning("Minimum value calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating minimum: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MEDIAN:
            try:
                # Handle the even number of data points case for median
                if len(values) % 2 == 0 and values:
                    sorted_values: list[float] = sorted(values)
                    middle1: float = sorted_values[len(values) // 2 - 1]
                    middle2: float = sorted_values[len(values) // 2]
                    self._attr_native_value = (middle1 + middle2) / 2
                    _LOGGER.warning(
                        "Median calculated from even number of values (%d): %s (middle values: %s, %s)",
                        len(values), self._attr_native_value, middle1, middle2
                    )
                else:
                    self._attr_native_value = statistics.median(values)
                    _LOGGER.warning("Median calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating median: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MEAN:
            try:
                self._attr_native_value = statistics.mean(values)
                _LOGGER.warning("Mean value calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating mean: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_STD_DEV:
            try:
                # Handle edge cases for standard deviation
                if len(values) == 1:
                    self._attr_native_value = "unknown"
                    _LOGGER.warning("Standard deviation with one value: setting to 'unknown'")
                elif len(values) == 2:
                    self._attr_native_value = 0
                    _LOGGER.warning("Standard deviation with two values: setting to 0")
                else:
                    self._attr_native_value = statistics.stdev(values)
                    _LOGGER.warning("Standard deviation calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating standard deviation: %s", ex)
                self._attr_native_value = None
        
        self.async_write_ha_state()
