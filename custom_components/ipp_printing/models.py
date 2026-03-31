from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.util.hass_dict import HassKey
from .const import DOMAIN


@dataclass
class IPPPrintingDomainConfig:
    """Class for sharing config data within the IPP printing integration."""

    pass


@dataclass
class IPPPrintingData:
    """Class for sharing data within the IPP printing integration."""

    domain_config: IPPPrintingDomainConfig


type IPPPrintingConfigEntry = ConfigEntry[IPPPrintingData]

MY_KEY: HassKey[IPPPrintingDomainConfig] = HassKey(DOMAIN)
