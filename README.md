# Day of Month Sensor for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs-shield]][hacs]

![Project Maintenance][maintenance-shield]

**Current Version:** 0.1.3  
**Requires:** Home Assistant 2024.12.0+ | HACS 2.0.0+

This custom integration for Home Assistant creates a sensor that calculates values based on historical data from existing sensors. It allows you to track patterns and trends over time by analyzing long-term statistics.

## Features

- Create sensors that calculate aggregations (maximum, minimum, median, mean, standard deviation) of historical data of existing sensors
- Filter historical data by annual or monthly patterns (same day of year or same day of month)
- Choose which historical data value to track (mean, min, max, state)
- Configure sensor update frequency (hourly or daily)
- Easy setup through the UI with config flow
- Automatically inherits unit of measurement from the existing sensor entity
- Specialized handling for statistical edge cases

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL of this repository
   - Select "Integration" as the category
3. Click "Install" on the Day of Month Sensor integration
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the releases page
2. Unpack the release and copy the `custom_components/day_of_month_sensor` directory into your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click the "+ Add Integration" button
3. Search for "Day of Month Sensor" and select it
4. Follow the configuration flow:
   - Select a source entity (must be a numeric sensor with a valid state class)
   - Choose which historic data value to track (mean, min, max, state)
   - Select an aggregation method (maximum, minimum, median, mean, standard deviation)
   - Choose a historic filter range (annual or monthly)
   - Set the update frequency (hourly or daily)

## How It Works

The Day of Month Sensor integration analyzes long-term statistics for the selected entity and calculates values based on your configuration:

- **Track Value**: Determines which field in the long-term statistics to use (mean, min, max, or state)
- **Aggregation**: The mathematical operation to perform on the filtered data
- **Historic Range**:
  - Annual: Only considers data from the same day and month across years
  - Monthly: Only considers data from the same day across months
- **Update Frequency**:
  - Hourly: Updates 24 times per day when long-term statistics are updated
  - Daily: Updates once per day using the final value for the day
- **Edge Case Handling**:
  - Standard deviation with one data point: Returns "unknown"
  - Standard deviation with two data points: Returns 0
  - Median with even number of data points: Returns average of the two middle values

## Examples

### Example 1: Annual Temperature Patterns

Create a sensor that shows the average temperature for today's date across all years:

- Source Entity: Your temperature sensor
- Track Value: mean
- Aggregation: mean
- Historic Range: annual
- Update Frequency: daily

This will show you the typical temperature for this day of the year based on historical data.

### Example 2: Monthly Energy Usage Patterns

Create a sensor that shows the maximum energy usage for this day of the month:

- Source Entity: Your energy consumption sensor
- Track Value: max
- Aggregation: maximum
- Historic Range: monthly
- Update Frequency: hourly

This will show you the highest energy usage recorded on this day of the month across different months.

## Troubleshooting

- The sensor requires historical statistics data to be available. Make sure your Home Assistant instance has been recording statistics for the source entity.
- For best results, use a source entity that has been recording data for a significant period.
- If the sensor shows "unknown" or "unavailable", check that there is sufficient historical data available for the calculation.
- The sensor automatically inherits the unit of measurement from the source entity.

## Development

### Release Process (Note to self)

This integration uses GitHub Actions to automate the release process. When a new version is ready to be released:

1. Update the version number in `custom_components/day_of_month_sensor/manifest.json`
2. Update `CHANGELOG.md` with a new section for the version (e.g., `## 0.1.2`)
3. Commit these changes: `git commit -m "Bump version to 0.1.2"`
4. Create and push a tag matching the version:
   ```
   git tag v0.1.2
   git push origin v0.1.2
   ```

The GitHub release will be used by HACS to make the new version available to users.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/rahulpdev/hassDailySensor.svg
[commits]: https://github.com/rahulpdev/hassDailySensor/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs]: https://github.com/hacs/integration
[license-shield]: https://img.shields.io/github/license/rahulpdev/hassDailySensor.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2025.svg
[releases-shield]: https://img.shields.io/github/release/rahulpdev/hassDailySensor.svg
[releases]: https://github.com/rahulpdev/hassDailySensor/releases
