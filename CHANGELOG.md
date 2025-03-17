# Changelog

## 0.1.3 (2025-03-17)

### Changes

- Optimized database queries by targeting specific dates instead of fetching a full year of data
- Reduced processing overhead by eliminating post-query filtering
- Changed log level from warning to debug for normal operation logs
- Added new method to generate target dates based on historic range

## 0.1.2 (2025-03-17)

### Changes

- Fixed database access warning by using the recorder's executor for database operations
- Improved performance of database operations

## 0.1.1 (2025-03-13)

### Changes

- Renamed integration from "Daily Sensor" to "Day of Month Sensor"
- Updated version requirements for Home Assistant and HACS

## 0.1.0 (2025-03-12)

### Initial Release

- Create sensors that calculate aggregations of historical data
- Filter historical data by annual or monthly patterns
- Choose which historical value to track (mean, min, max, state)
- Configure sensor update frequency (hourly or daily)
- Easy setup through the UI with config flow
- Support for inheriting unit of measurement from source entity
