"""Constants for the Day of Month Sensor integration."""
from typing import Final

DOMAIN: Final = "day_of_month_sensor"

# Configuration keys
CONF_ENTITY_ID: Final = "entity_id"
CONF_TRACK_VALUE: Final = "track_value"
CONF_AGGREGATION: Final = "aggregation"
CONF_HISTORIC_RANGE: Final = "historic_range"
CONF_UPDATE_FREQUENCY: Final = "update_frequency"

# Track value options
TRACK_VALUE_MEAN: Final = "mean"
TRACK_VALUE_MIN: Final = "min"
TRACK_VALUE_MAX: Final = "max"
TRACK_VALUE_STATE: Final = "state"

TRACK_VALUE_OPTIONS: Final = [
    TRACK_VALUE_MEAN,
    TRACK_VALUE_MIN,
    TRACK_VALUE_MAX,
    TRACK_VALUE_STATE,
]

# Aggregation options
AGGREGATION_MAXIMUM: Final = "maximum"
AGGREGATION_MINIMUM: Final = "minimum"
AGGREGATION_MEDIAN: Final = "median"
AGGREGATION_MEAN: Final = "mean"
AGGREGATION_STD_DEV: Final = "standard deviation"

AGGREGATION_OPTIONS: Final = [
    AGGREGATION_MAXIMUM,
    AGGREGATION_MINIMUM,
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN,
    AGGREGATION_STD_DEV,
]

# Historic range options
HISTORIC_RANGE_ANNUAL: Final = "annual"
HISTORIC_RANGE_MONTHLY: Final = "monthly"

HISTORIC_RANGE_OPTIONS: Final = [
    HISTORIC_RANGE_ANNUAL,
    HISTORIC_RANGE_MONTHLY,
]

# Update frequency options
UPDATE_FREQUENCY_HOURLY: Final = "hourly"
UPDATE_FREQUENCY_DAILY: Final = "daily"

UPDATE_FREQUENCY_OPTIONS: Final = [
    UPDATE_FREQUENCY_HOURLY,
    UPDATE_FREQUENCY_DAILY,
]

# Valid state classes for source entities
VALID_STATE_CLASSES: Final = [
    "measurement",
    "total",
    "total_increasing",
    "calculation",
]

# Attributes
ATTR_TRACK_VALUE: Final = "track_value"
ATTR_AGGREGATION: Final = "aggregation"
ATTR_HISTORIC_RANGE: Final = "historic_range"
