"""Platform for sensor integration."""
from __future__ import annotations
from datetime import timedelta
import logging

from mypermobil import (
    BATTERY_AMPERE_HOURS_LEFT,
    BATTERY_CHARGE_TIME_LEFT,
    BATTERY_CHARGING,
    BATTERY_INDOOR_DRIVE_TIME,
    BATTERY_LOCAL_DISTANCE_LEFT,
    BATTERY_MAX_AMPERE_HOURS,
    BATTERY_MAX_DISTANCE_LEFT,
    BATTERY_STATE_OF_CHARGE,
    BATTERY_STATE_OF_HEALTH,
    POSITIONS_CURRENT,
    RECORDS_DISTANCE,
    RECORDS_SEATING,
    USAGE_ADJUSTMENTS,
    USAGE_DISTANCE,
    MyPermobil,
    MyPermobilException,
)

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    API,
    BATTERY_ASSUMED_VOLTAGE,
    DOMAIN,
    LATITUDE,
    LONGITUDE,
    MILES_PER_KILOMETER,
    UNIT,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=50)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    # translate the Permobils unit of distance to a Home Assistant unit of distance
    # default to kilometers if the unit is unknown
    p_api = hass.data[DOMAIN][API][config_entry.entry_id]
    ha_unit = hass.data[DOMAIN][UNIT][config_entry.entry_id]

    user_specific_sensors = [
        PermobilDistanceLeftSensor(p_api, unit=ha_unit),
        PermobilMaxDistanceLeftSensor(p_api, unit=ha_unit),
        PermobilUsageDistanceSensor(p_api, unit=ha_unit),
        PermobilRecordDistanceSensor(p_api, unit=ha_unit),
    ]

    # create the sensors that are not user specific
    non_specific_sensors = [
        PermobilStateOfChargeSensor(p_api),
        PermobilStateOfHealthSensor(p_api),
        PermobilChargingSensor(p_api),
        PermobilChargeTimeLeftSensor(p_api),
        PermobilIndoorDriveTimeSensor(p_api),
        PermobilMaxWattHoursSensor(p_api),
        PermobilWattHoursLeftSensor(p_api),
        PermobilUsageAdjustmentsSensor(p_api),
        PermobilRecordAdjustmentsSensor(p_api),
        PermobilPositionSensor(p_api),
    ]

    sensors = non_specific_sensors + user_specific_sensors
    async_add_entities(sensors, update_before_add=True)


class PermobilGenericSensor(SensorEntity):
    """Representation of a Sensor.

    This implements the common functions of all sensors.
    """

    _attr_name = "Generic Sensor"

    def __init__(self, permobil: MyPermobil, item: list, unit: str = "") -> None:
        """Initialize the sensor.

        item: The item to request from the API.
        unit: The unit of measurement. (optional)
        """
        super().__init__()
        self._permobil = permobil
        self._item = item
        if unit:
            self._attr_native_unit_of_measurement = unit

    async def async_update(self) -> None:
        """Get the latest data from the API."""
        try:
            self._attr_native_value = await self._permobil.request_item(self._item)
            if self._attr_native_value is None:
                _LOGGER.error("Sensor returned none: %s", self._attr_name)
            if isinstance(self._attr_native_value, float):
                self._attr_native_value = round(self._attr_native_value, 2)

        except MyPermobilException as err:
            _LOGGER.error("Error while fetching %s: %s", self._attr_name, err)
            self._attr_native_value = None


class PermobilStateOfChargeSensor(PermobilGenericSensor):
    """Batter percentage sensor."""

    _attr_name = "Permobil Battery Charge"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_STATE_OF_CHARGE)


class PermobilStateOfHealthSensor(PermobilGenericSensor):
    """Battery health sensor."""

    _attr_name = "Permobil Battery Health"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_STATE_OF_HEALTH)


class PermobilChargingSensor(BinarySensorEntity):
    """Battery charging sensor.

    This is a binary sensor because it can only be on or off.
    """

    _attr_name = "Permobil is Charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor.

        this is a binary sensor and has a different constructor.
        """
        super().__init__()
        self._permobil = permobil
        self._item = BATTERY_CHARGING

    async def async_update(self) -> None:
        """Get charging status."""
        try:
            self._attr_is_on = bool(await self._permobil.request_item(self._item))
        except MyPermobilException:
            # if we can't get the charging status, assume it is not charging
            self._attr_is_on = None


class PermobilChargeTimeLeftSensor(PermobilGenericSensor):
    """Battery charge time left sensor."""

    _attr_name = "Permobil Charge Time Left"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_CHARGE_TIME_LEFT)


class PermobilDistanceLeftSensor(PermobilGenericSensor):
    """Battery distance left sensor."""

    _attr_name = "Permobil Distance Left"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil, unit: UnitOfLength) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_LOCAL_DISTANCE_LEFT, unit)


class PermobilIndoorDriveTimeSensor(PermobilGenericSensor):
    """Battery indoor drive time sensor."""

    _attr_name = "Permobil Indoor Drive Time"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_INDOOR_DRIVE_TIME)


class PermobilMaxWattHoursSensor(PermobilGenericSensor):
    """Battery max watt hours sensor.

    converted from ampere hours by multiplying with voltage.
    """

    _attr_name = "Permobil Battery Max Watt Hours"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_value: float | None = None

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_MAX_AMPERE_HOURS)

    async def async_update(self) -> None:
        """Get battery percentage.

        This is multiplied with the assumed voltage of the battery to get the watt hours.
        """
        await super().async_update()
        if self._attr_native_value:
            self._attr_native_value *= BATTERY_ASSUMED_VOLTAGE
            self._attr_native_value = int(self._attr_native_value)


class PermobilWattHoursLeftSensor(PermobilGenericSensor):
    """Battery ampere hours left sensor.

    converted from ampere hours by multiplying with voltage.
    """

    _attr_name = "Permobil Watt Hours Left"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_value: float | None = None

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_AMPERE_HOURS_LEFT)

    async def async_update(self) -> None:
        """Get battery percentage.

        This is multiplied with the assumed voltage of the battery to get the watt hours.
        """
        await super().async_update()
        if self._attr_native_value:
            self._attr_native_value *= BATTERY_ASSUMED_VOLTAGE
            self._attr_native_value = int(self._attr_native_value)


class PermobilMaxDistanceLeftSensor(PermobilGenericSensor):
    """Battery max distance left sensor."""

    _attr_name = "Permobil Full Charge Distance"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil, unit: UnitOfLength) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, BATTERY_MAX_DISTANCE_LEFT, unit)

    async def async_update(self) -> None:
        """Get Max Distance left.

        since the api returns the distance in KM it needs to be converted if the
        user is using miles.
        """
        await super().async_update()
        if (
            isinstance(self._attr_native_value, float | int)
        ) and self._attr_native_unit_of_measurement == UnitOfLength.MILES:
            self._attr_native_value *= MILES_PER_KILOMETER
            self._attr_native_value = round(self._attr_native_value, 2)


class PermobilUsageDistanceSensor(PermobilGenericSensor):
    """usage distance sensor."""

    _attr_name = "Permobil Distance Traveled"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil, unit: UnitOfLength) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, USAGE_DISTANCE, unit)


class PermobilUsageAdjustmentsSensor(PermobilGenericSensor):
    """usage adjustments sensor."""

    _attr_name = "Permobil Number of Adjustments"
    _attr_native_unit_of_measurement = "adjustments"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, USAGE_ADJUSTMENTS)


class PermobilRecordDistanceSensor(PermobilGenericSensor):
    """record distance sensor."""

    _attr_name = "Permobil Record Distance Traveled"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil, unit: UnitOfLength) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, RECORDS_DISTANCE, unit)


class PermobilRecordAdjustmentsSensor(PermobilGenericSensor):
    """record adjustments sensor."""

    _attr_name = "Permobil Record Number of Adjustments"
    _attr_native_unit_of_measurement = "adjustments"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, RECORDS_SEATING)


class PermobilPositionSensor(PermobilGenericSensor):
    """Position of wheelchair sensor."""

    _attr_name = "Permobil Position Sensor"
    _show_on_map = True

    def __init__(self, permobil: MyPermobil) -> None:
        """Initialize the sensor."""
        super().__init__(permobil, POSITIONS_CURRENT)
        self._location_data: dict | None = None

    async def async_update(self) -> None:
        """Get battery and position information."""
        await super().async_update()
        if not isinstance(self._attr_native_value, dict):
            self._location_data = None
            self._attr_native_value = "Unknown"
            return

        long = self._attr_native_value.get(LONGITUDE)
        lat = self._attr_native_value.get(LATITUDE)
        if not long or not lat:
            self._location_data = None
            self._attr_native_value = "Unknown"
            return

        self._location_data = {
            ATTR_LONGITUDE: str(long),
            ATTR_LATITUDE: str(lat),
        }
        self._attr_native_value = "Visible on Map"

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return latitude value of the device."""
        return self._location_data
