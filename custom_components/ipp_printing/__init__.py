"""The IPP printing integration."""

from __future__ import annotations

import logging
import base64
import homeassistant.helpers.device_registry as dr

from typing import cast

from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.ipp.coordinator import IPPConfigEntry
from homeassistant.util.json import JsonValueType
from homeassistant.helpers import config_validation as cv
from homeassistant.core import (
    ServiceCall,
    HomeAssistant,
    callback,
    ServiceResponse,
    SupportsResponse,
)
from .const import DOMAIN
from .helpers import print_to_ipp, get_printer_information_helper
from .models import (
    IPPPrintingConfigEntry,
    IPPPrintingData,
    MY_KEY,
    IPPPrintingDomainConfig,
)


PLATFORMS: list[Platform] = []
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def device_id_to_config_entry(
    hass: HomeAssistant, device_id: str
) -> IPPConfigEntry | None:
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(device_id)
    if device_entry is None:
        return None
    matching_config_entries = cast(
        list[IPPConfigEntry],
        [
            c
            for c in hass.config_entries.async_loaded_entries(domain="ipp")
            if c.entry_id in device_entry.config_entries
        ],
    )
    if not matching_config_entries:
        return None
    return matching_config_entries[0]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Integration setup."""

    domain_config = IPPPrintingDomainConfig()

    hass.data[MY_KEY] = domain_config

    @callback
    async def print_helper(service: ServiceCall) -> ServiceResponse:
        data = base64.b64decode(service.data["data"])
        mimetype = service.data["mimetype"]
        device_id = service.data["device"]
        conf = device_id_to_config_entry(hass, device_id)
        if conf is None:
            raise HomeAssistantError(
                "Cannot find the configuration for device %s" % device_id
            )
        job = await print_to_ipp(
            hass,
            conf,
            data,
            mimetype,
            quality=service.data.get("quality", None),
            scaling=service.data.get("scaling", None),
            paper_size=service.data.get("paper_size", None),
            fidelity=service.data.get("fidelity", None),
            orientation=service.data.get("orientation", None),
        )
        return {"job": job}

    @callback
    async def print_information_service(service: ServiceCall) -> ServiceResponse:
        device_id = service.data["device"]
        conf = device_id_to_config_entry(hass, device_id)
        if conf is None:
            raise HomeAssistantError(
                "Cannot find the configuration for device %s" % device_id
            )
        printer_data, jobs = await get_printer_information_helper(
            hass,
            conf,
            get_complete_jobs=service.data.get("job_filter", "incomplete")
            in ["all", "complete"],
            get_incomplete_jobs=service.data.get("job_filter", "incomplete")
            in ["all", "incomplete"],
        )
        pr: ServiceResponse = {"printer": printer_data, "jobs": jobs}
        return pr

    hass.services.async_register(
        DOMAIN,
        "print",
        print_helper,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        "get_printer_information",
        print_information_service,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: IPPPrintingConfigEntry,
) -> bool:
    """Set up a config entry."""

    domain_config = hass.data[MY_KEY]

    config_entry.runtime_data = IPPPrintingData(
        domain_config=domain_config,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: IPPPrintingConfigEntry,
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant,
    config_entry: IPPPrintingConfigEntry,
) -> None:
    """Integration removed."""
    pass
