"""Support for Navien NaviLink water heaters."""
import logging

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, TEMP_CELCIUS, TEMP_FARENHEIT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)
from .navien_api import (
    NavienSmartControl,
    DeviceSorting,
    TemperatureType
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.AWAY_MODE
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Navien water heater based on a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    username = entry.title.replace("navien_","")
    devices = []
    for gatewayID, channelInfo in entry.data:
        for channelNum in range(1,4):
            if channelInfo["channel"][str[channelNum]]["deviceSorting"] != DeviceSorting.NO_DEVICE.value:
                devices.append(NavienWaterHeaterEntity(username, channelInfo, channelNum, coordinators[gatewayID]))
    async_add_entities(devices)


class NavienWaterHeaterEntity(CoordinatorEntity, WaterHeaterEntity):
    """Define a Navien water heater."""
 
    def __init__(self, username, channelInfo, channelNum, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self.deviceNum = 1
        self.navien = NavienSmartControl(username)
        self.channelNum = channelNum
        self.channelInfo = channelInfo
        self.state = self.coordinator.data[str(channelNum)][str(self.deviceNum)]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.state = self.coordinator.data[str(self.channelNum)][str(self.deviceNum)]
        self.async_write_ha_state()

    @property
    def temperature_unit(self):
        """Return temperature unit."""
        temp_unit = TEMP_CELCIUS
        if self.channelInfo["channel"][str(self.channelNum)]["deviceTempFlag"] == TemperatureType.FAHRENHEIT.value:
            temp_unit = TEMP_FARENHEIT

        return temp_unit

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return not(self.state["powerStatus"])

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def current_temperature(self):
        """Return the temperature we try to reach."""
        return self.state["hotWaterTemperature"]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.state["hotWaterSettingTemperature"]

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self.channelInfo["channel"][str(self.channelNum)]["minimumSettingWaterTemperature"]

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self.channelInfo["channel"][str(self.channelNum)]["maximumSettingWaterTemperature"]

    async def async_set_temperature(self,**kwargs):
        """Set target water temperature"""
        if (target_temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.navien.connect(bytes.hex(self.channelInfo["deviceID"]))
            await self.navien.sendWaterTempControlRequest(self.channelInfo["deviceID"],self.channelNum,self.deviceNum,target_temp)
            await self.navien.disconnect()
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("A target temperature must be provided")

    async def async_turn_away_mode_on(self):
        """Turn away mode on."""
        await self.navien.connect(bytes.hex(self.channelInfo["deviceID"]))
        await self.navien.sendPowerControlRequest(self.channelInfo["deviceID"],self.channelNum,self.deviceNum,2)
        await self.navien.disconnect()
        await self.coordinator.async_request_refresh()


    async def async_turn_away_mode_off(self):
        """Turn away mode off."""
        await self.navien.connect(bytes.hex(self.channelInfo["deviceID"]))
        await self.navien.sendPowerControlRequest(self.channelInfo["deviceID"],self.channelNum,self.deviceNum,1)
        await self.navien.disconnect()
        await self.coordinator.async_request_refresh()
