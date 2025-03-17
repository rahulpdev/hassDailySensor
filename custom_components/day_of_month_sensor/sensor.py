"""Platform for Day of Month Sensor integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import statistics
from typing import Any, Callable, Optional

from homeassistant.components.recorder import get_instance
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
from homeassistant.core import HomeAssistant, State
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


def safe_convert_to_datetime(timestamp_value: Any) -> Optional[datetime]:
    """Safely convert a timestamp value to a datetime object.
    
    Args:
        timestamp_value: The timestamp value to convert, can be a float, int, 
                        string, or datetime object.
                        
    Returns:
        Optional[datetime]: A datetime object if conversion was successful, 
                           None otherwise.
    """
    try:
        if isinstance(timestamp_value, (int, float)):
            # Convert numeric timestamp to datetime
            return dt_util.utc_from_timestamp(timestamp_value)
        elif isinstance(timestamp_value, datetime):
            # Already a datetime, just return it
            return timestamp_value
        elif isinstance(timestamp_value, str):
            # Try to parse string as datetime
            try:
                return dt_util.parse_datetime(timestamp_value)
            except (ValueError, TypeError):
                # If parsing fails, try to convert to float first
                return dt_util.utc_from_timestamp(float(timestamp_value))
        else:
            _LOGGER.error("Unsupported timestamp type: %s", type(timestamp_value))
            return None
    except Exception as ex:
        _LOGGER.error("Error converting timestamp %s: %s", timestamp_value, ex)
        return None


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
        self._remove_update_listener: Optional[Callable[[], None]] = None
        self._attr_native_value: Optional[float] = None
        self._attr_native_unit_of_measurement: Optional[str] = None

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
            try:
                # Try to convert state to float for measurement state class
                self._attr_native_value = float(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert previous state '%s' to float, using None",
                    state.state
                )
                self._attr_native_value = None
            
            # Restore attributes
            if ATTR_UNIT_OF_MEASUREMENT in state.attributes:
                self._attr_native_unit_of_measurement = state.attributes[
                    ATTR_UNIT_OF_MEASUREMENT
                ]
        
        # Get the unit of measurement from the source entity
        source_state: Optional[State] = self.hass.states.get(self._entity_id)
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

    def _generate_target_dates(self, now: datetime) -> list[datetime]:
        """Generate a list of target dates based on historic range.
        
        This method calculates the specific dates that match the historic range
        criteria (same day of month for monthly, same day and month for annual).
        
        Args:
            now: The current datetime.
            
        Returns:
            list[datetime]: A list of datetime objects representing the target dates.
        """
        target_dates = []
        current_date = now
        
        # For annual range, we look back up to 10 years
        # For monthly range, we look back up to 12 months
        max_lookback = 10 if self._historic_range == HISTORIC_RANGE_ANNUAL else 12
        lookback_unit = 'years' if self._historic_range == HISTORIC_RANGE_ANNUAL else 'months'
        
        _LOGGER.debug(
            "Generating target dates for historic range: %s (current day: %d, month: %d)",
            self._historic_range,
            now.day,
            now.month
        )
        
        # Start with current date and go back in time
        for i in range(max_lookback):
            if lookback_unit == 'years':
                # Go back i years from now
                target_date = current_date.replace(year=current_date.year - i)
            else:  # months
                # Go back i months from now
                year_diff = i // 12
                month = current_date.month - (i % 12)
                if month <= 0:
                    month += 12
                    year_diff += 1
                target_date = current_date.replace(year=current_date.year - year_diff, month=month)
            
            # Handle cases where the day doesn't exist in the target month (e.g., Feb 29)
            try:
                target_date = target_date.replace(day=now.day)
                target_dates.append(target_date)
                _LOGGER.debug("Added target date: %s", target_date)
            except ValueError:
                _LOGGER.debug("Skipping invalid date (day doesn't exist in month): %s", target_date)
                continue
        
        return target_dates

    async def _async_update(self, _now: Optional[datetime] = None) -> None:
        """Update the sensor state.
        
        This method fetches statistics for the source entity for specific dates
        that match the historic range criteria, extracts the values to track,
        and calculates the aggregation.
        
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
                _LOGGER.debug("Fetching daily statistics for entity: %s", self._entity_id)
                stats: list[dict[str, Any]] = await get_instance(self.hass).async_add_executor_job(
                    get_last_statistics,
                    self.hass,
                    1,  # Get the most recent statistic
                    self._entity_id,
                    True,  # Include the current day
                )
                _LOGGER.debug("Retrieved %d daily statistics records", len(stats))
            else:
                # For hourly updates, get statistics only for the target dates
                target_dates = self._generate_target_dates(now)
                _LOGGER.debug(
                    "Fetching hourly statistics for entity: %s (for %d specific dates)",
                    self._entity_id,
                    len(target_dates)
                )
                
                # Collect statistics for each target date
                all_stats = []
                for target_date in target_dates:
                    # Create start and end time for the target date (full day)
                    start_time = dt_util.as_utc(dt_util.start_of_local_day(target_date))
                    end_time = dt_util.as_utc(dt_util.start_of_local_day(target_date + timedelta(days=1)))
                    
                    _LOGGER.debug("Fetching statistics for date: %s (start: %s, end: %s)",
                                 target_date.strftime("%Y-%m-%d"), start_time, end_time)
                    
                    # Fetch statistics for this specific date
                    stats_result: dict[str, list[dict[str, Any]]] = await get_instance(self.hass).async_add_executor_job(
                        statistics_during_period,
                        self.hass,
                        start_time,
                        end_time,
                        [self._entity_id],
                        "hour",  # Hourly statistics
                        None,  # No units conversion
                        {"sum", "mean", "min", "max", "state"},  # All statistic types
                    )
                    
                    date_stats = stats_result.get(self._entity_id, [])
                    all_stats.extend(date_stats)
                    _LOGGER.debug("Retrieved %d statistics records for date %s",
                                 len(date_stats), target_date.strftime("%Y-%m-%d"))
                
                stats = all_stats
                _LOGGER.debug("Retrieved %d total hourly statistics records", len(stats))
                
                # Log a sample of the statistics data
                if stats:
                    sample = stats[0]
                    _LOGGER.debug(
                        "Sample statistic record: start=%s, fields=%s",
                        sample.get("start"),
                        {k: v for k, v in sample.items() if k != "start"}
                    )
        except Exception as ex:
            _LOGGER.error("Error getting statistics: %s", ex)
            self._attr_native_value = None
            self.async_write_ha_state()
            return
        
        # Log some sample dates from stats
        if stats:
            try:
                sample_dates = []
                for stat in stats[:3]:
                    start_time_dt = safe_convert_to_datetime(stat["start"])
                    if start_time_dt:
                        local_dt = dt_util.as_local(start_time_dt)
                        sample_dates.append(local_dt.strftime("%Y-%m-%d %H:%M"))
                
                _LOGGER.debug("Sample dates from statistics: %s", sample_dates)
            except Exception as ex:
                _LOGGER.error("Error creating sample dates: %s", ex)
        
        # Extract the values to track from the statistics
        values: list[float] = []
        _LOGGER.debug("Extracting '%s' values from statistics", self._track_value)
        
        for stat in stats:
            try:
                if self._track_value == TRACK_VALUE_MEAN and "mean" in stat:
                    values.append(float(stat["mean"]))
                elif self._track_value == TRACK_VALUE_MIN and "min" in stat:
                    values.append(float(stat["min"]))
                elif self._track_value == TRACK_VALUE_MAX and "max" in stat:
                    values.append(float(stat["max"]))
                elif self._track_value == TRACK_VALUE_STATE and "state" in stat:
                    values.append(float(stat["state"]))
            except (ValueError, TypeError) as ex:
                _LOGGER.error("Error extracting value from stat: %s - %s", stat, ex)
        
        _LOGGER.debug("Extracted %d values for '%s'", len(values), self._track_value)
        
        # Log the extracted values
        if values:
            try:
                sample_values = [round(v, 2) for v in values[:5]]
                _LOGGER.debug("Sample values (up to 5): %s", sample_values)
            except Exception as ex:
                _LOGGER.error("Error formatting sample values: %s", ex)
        
        # Calculate the aggregation
        _LOGGER.debug("Calculating '%s' aggregation on %d values", self._aggregation, len(values))
        
        if not values:
            _LOGGER.debug("No historical data found for %s", self._entity_id)
            self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MAXIMUM:
            try:
                self._attr_native_value = max(values)
                _LOGGER.debug("Maximum value calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating maximum: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MINIMUM:
            try:
                self._attr_native_value = min(values)
                _LOGGER.debug("Minimum value calculated: %s", self._attr_native_value)
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
                    _LOGGER.debug(
                        "Median calculated from even number of values (%d): %s (middle values: %s, %s)",
                        len(values), self._attr_native_value, middle1, middle2
                    )
                else:
                    self._attr_native_value = statistics.median(values)
                    _LOGGER.debug("Median calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating median: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_MEAN:
            try:
                self._attr_native_value = statistics.mean(values)
                _LOGGER.debug("Mean value calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating mean: %s", ex)
                self._attr_native_value = None
        elif self._aggregation == AGGREGATION_STD_DEV:
            try:
                # Handle edge cases for standard deviation
                if len(values) == 1:
                    self._attr_native_value = None
                    _LOGGER.debug("Standard deviation with one value: setting to None (unavailable)")
                elif len(values) == 2:
                    self._attr_native_value = 0
                    _LOGGER.debug("Standard deviation with two values: setting to 0")
                else:
                    self._attr_native_value = statistics.stdev(values)
                    _LOGGER.debug("Standard deviation calculated: %s", self._attr_native_value)
            except Exception as ex:
                _LOGGER.error("Error calculating standard deviation: %s", ex)
                self._attr_native_value = None
        
        self.async_write_ha_state()
