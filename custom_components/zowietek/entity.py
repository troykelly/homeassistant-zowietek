"""Base entity for Zowietek integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZowietekCoordinator

if TYPE_CHECKING:
    pass


class ZowietekEntity(CoordinatorEntity[ZowietekCoordinator]):
    """Base entity for Zowietek devices.

    All Zowietek entities inherit from this class to share common
    functionality including device registry integration and
    coordinator-based data updates.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator for this device.
            entity_key: A unique key identifying this entity type
                (e.g., "video_resolution", "ndi_enabled").
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{entity_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry.

        This information is used by Home Assistant to group entities
        under a single device in the device registry.

        Returns:
            DeviceInfo containing manufacturer, model, name, firmware version,
            serial number, and a link to the device's web UI.
        """
        # Get firmware version from system data
        sw_version = self.coordinator.data.system.get("firmware_version")
        if sw_version is not None:
            sw_version = str(sw_version)

        # Get serial number from system data
        serial_number = self.coordinator.data.system.get("devicesn")
        if serial_number is not None:
            serial_number = str(serial_number)

        # Get hardware version for hw_version field
        hw_version = self.coordinator.data.system.get("hardware_version")
        if hw_version is not None:
            hw_version = str(hw_version)

        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.config_entry.unique_id))},
            manufacturer=str(self.coordinator.data.system.get("manufacturer", "Zowietek")),
            model=str(self.coordinator.data.system.get("model", "ZowieBox")),
            name=self.coordinator.device_name,
            sw_version=sw_version,
            hw_version=hw_version,
            serial_number=serial_number,
            configuration_url=f"http://{self.coordinator.config_entry.data['host']}",
        )
