"""Config flow for the IPP printing integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult

from .const import (
    DOMAIN,
)
from .const import (
    NAME as INTEGRATION_NAME,
)

_LOGGER = logging.getLogger(__name__)


class IPPPrintingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IPP printing."""

    VERSION = 1

    async def async_get_integration_entry(self) -> ConfigEntry | None:
        """Return the main integration config entry, if it exists."""
        existing_entries = self.hass.config_entries.async_entries(
            domain=DOMAIN, include_ignore=False, include_disabled=False
        )
        for entry in existing_entries:
            if entry.title == INTEGRATION_NAME:
                return entry
        return None

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        # pylint: disable=unused-argument
        """Handle a flow initialized by the user."""

        if self._async_current_entries():
            _LOGGER.debug("An existing ipp_printing config entry already exists")
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_NAME, data={}, options={})

        self._set_confirm_only()
        return self.async_show_form(step_id="user")
