import logging
from datetime import timedelta
import async_timeout
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .spanet import SpaNetApiError

_LOGGER = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, spanet, spa_config):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=spa_config["name"],
            update_interval=timedelta(seconds=60),
        )
        self.spanet = spanet
        self.spa_config = spa_config
        self.spa = None

    @property
    def spa_name(self):
        return self.spa_config["name"]

    @property
    def spa_id(self):
        return self.spa_config["id"]

    def get_status(self, status_key: str):
        if not self.spa:
            return None
        return self.spa.get_status(status_key)

    def get_status_numeric(self, status_key: str, divisor=1):
        value = self.get_status(status_key)
        if value is None:
            return None
        return int(value) / divisor

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            if not self.spa:
                self.spa = await self.spanet.get_spa(self.spa_config["id"])
            async with async_timeout.timeout(10):
                return await self.spa.refresh_status()

        except SpaNetApiError as exc:
            _LOGGER.info('Connection lost')
            self.spa = None
            raise UpdateFailed("Failed updating spanet") from exc
