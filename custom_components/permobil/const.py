"""Constants for the MyPermobil integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

VERSION = "0.1.0"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"


NAME = "MyPermobil"
DOMAIN = "permobil"

APPLICATION = "Home Assistant"

API = "api"
REGIONS = "regions"
UNIT = "unit"

BATTERY_ASSUMED_VOLTAGE = 25.0  # This is the average voltage over all states of charge
MILES_PER_KILOMETER = 0.621371
KM = "kilometers"
MILES = "miles"

LATITUDE = "lat"
LONGITUDE = "long"
