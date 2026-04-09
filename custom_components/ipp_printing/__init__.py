"""The IPP printing integration."""

from __future__ import annotations

import base64
from typing import cast

import homeassistant.helpers.device_registry as dr
from homeassistant.components.ipp.coordinator import IPPConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .helpers import get_printer_information_helper, print_to_ipp, get_device_id
from .models import (
    MY_KEY,
    IPPPrintingConfigEntry,
    IPPPrintingData,
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
    async def print_helper(call: ServiceCall) -> ServiceResponse:
        if "data" in call.data:
            if "mimetype" not in call.data:
                raise ServiceValidationError(
                    "cannot request `data` to be printed without a `mimetype`"
                )
            if "text" in call.data:
                raise ServiceValidationError(
                    "cannot request both `data` and `text` to be printed"
                )
            data = base64.b64decode(call.data["data"])
            mimetype = call.data["mimetype"]
        elif "text" in call.data:
            if "mimetype" in call.data:
                raise ServiceValidationError(
                    "cannot request `text` to be printed with a `mimetype`"
                )
            data = str(call.data["text"]).encode("utf-8")
            mimetype = "text/plain; charset=utf-8"
        else:
            raise ServiceValidationError(
                "at least one of `data` plus `mimetype`, or `text`, is required"
            )

        device_id = get_device_id(hass, call)
        conf = device_id_to_config_entry(hass, device_id)
        if conf is None:
            raise HomeAssistantError(
                "Cannot find the configuration for device %s" % device_id
            )
        try:
            job = await print_to_ipp(
                hass,
                conf,
                data,
                mimetype,
                quality=call.data.get("quality", None),
                scaling=call.data.get("scaling", None),
                paper_size=call.data.get("paper_size", None),
                fidelity=call.data.get("fidelity", None),
                orientation=call.data.get("orientation", None),
            )
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e
        return {"job": job}

    @callback
    async def print_information_service(call: ServiceCall) -> ServiceResponse:
        device_id = get_device_id(hass, call)
        conf = device_id_to_config_entry(hass, device_id)
        if conf is None:
            raise HomeAssistantError(
                "Cannot find the configuration for device %s" % device_id
            )
        printer_data, jobs = await get_printer_information_helper(
            hass,
            conf,
            get_complete_jobs=call.data.get("job_filter", "incomplete")
            in ["all", "complete"],
            get_incomplete_jobs=call.data.get("job_filter", "incomplete")
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
