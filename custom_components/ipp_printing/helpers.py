"""IPP printing integration services."""

import logging
from typing import Literal, cast, Any

import pyipp
import pyipp.const
import pyipp.enums
import pyipp.exceptions
from homeassistant.components.ipp.const import CONF_BASE_PATH, DOMAIN as IPP_DOMAIN
from homeassistant.components.ipp.coordinator import IPPConfigEntry
from homeassistant.const import (
    CONF_HOST,
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.group import expand_entity_ids
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.json import JsonValueType

_LOGGER = logging.getLogger(__name__)


def munge_jobs(jobs: list[dict[str, JsonValueType]]) -> list[dict[str, JsonValueType]]:
    new_jobs: list[dict[str, JsonValueType]] = []
    for job in jobs:
        job = job.copy()
        job_state: int = cast(int, job["job-state"])
        state_enum = pyipp.enums.IppJobState(job_state).name.lower()
        job["job-state"] = state_enum
        new_jobs.append(job)
    return new_jobs


async def print_to_ipp(
    hass: HomeAssistant,
    conf: IPPConfigEntry,
    data: bytes,
    mimetype: str,
    quality: Literal["draft"] | Literal["normal"] | Literal["high"] | None,
    scaling: Literal["none"]
    | Literal["auto"]
    | Literal["auto-fit"]
    | Literal["fill"]
    | Literal["fit"]
    | None,
    paper_size: str | None,
    fidelity: bool | None,
    orientation: Literal["portrait"]
    | Literal["landscape"]
    | Literal["reverse-portrait"]
    | Literal["reverse-landscape"]
    | None,
) -> dict[str, JsonValueType]:
    async with pyipp.IPP(
        host=conf.data[CONF_HOST],
        port=conf.data[CONF_PORT],
        base_path=conf.data[CONF_BASE_PATH],
        tls=conf.data[CONF_SSL],
        verify_ssl=conf.data[CONF_VERIFY_SSL],
        session=async_get_clientsession(hass, conf.data[CONF_VERIFY_SSL]),
    ) as ipp:
        # monkey patch PyIPP deficiencies.
        # PRs:
        # * https://github.com/ctalkington/python-ipp/pull/720
        # * https://github.com/ctalkington/python-ipp/pull/721
        # * https://github.com/ctalkington/python-ipp/pull/722
        saved_media_tag = None

        from pyipp.tags import ATTRIBUTE_TAG_MAP

        if "print-scaling" not in ATTRIBUTE_TAG_MAP:
            ATTRIBUTE_TAG_MAP["print-scaling"] = pyipp.enums.IppTag.KEYWORD

        saved_media_tag = ATTRIBUTE_TAG_MAP["media"]
        ATTRIBUTE_TAG_MAP["media"] = pyipp.enums.IppTag.KEYWORD
        # End monkey-patching.

        try:
            opattrs: dict[str, JsonValueType] = {
                "document-format": mimetype,
            }
            if fidelity is not None:
                opattrs["ipp-attribute-fidelity"] = fidelity

            jobattrs: dict[str, JsonValueType] = {}
            if quality is not None:
                q = pyipp.enums.IppPrintQuality
                if quality == "draft":
                    jobattrs["print-quality"] = int(q.DRAFT)
                elif quality == "normal":
                    jobattrs["print-quality"] = int(q.NORMAL)
                elif quality == "high":
                    jobattrs["print-quality"] = int(q.HIGH)
                else:
                    raise ValueError("invalid quality %r" % (quality,))
            if orientation is not None:
                o = pyipp.enums.IppOrientationRequested
                if orientation == "portrait":
                    jobattrs["orientation-requested"] = int(o.PORTRAIT)
                elif orientation == "landscape":
                    jobattrs["orientation-requested"] = int(o.LANDSCAPE)
                elif orientation == "reverse-portrait":
                    jobattrs["orientation-requested"] = int(o.REVERSE_PORTRAIT)
                elif orientation == "reverse-landscape":
                    jobattrs["orientation-requested"] = int(o.REVERSE_LANDSCAPE)
                else:
                    raise ValueError("invalid orientation %r" % (orientation,))
            if scaling is not None:
                if scaling not in ["none", "auto", "auto-fit", "fill", "fit"]:
                    raise ValueError("invalid scaling %r" % (scaling,))
                # monkey patch PyIPP deficiency.
                from pyipp.tags import ATTRIBUTE_TAG_MAP

                if "print-scaling" not in ATTRIBUTE_TAG_MAP:
                    ATTRIBUTE_TAG_MAP["print-scaling"] = pyipp.enums.IppTag.KEYWORD
                jobattrs["print-scaling"] = scaling
            if paper_size is not None:
                jobattrs["media"] = paper_size

            pp: dict[str, JsonValueType | bytes] = {
                "operation-attributes-tag": opattrs,
                "data": data,
            }
            if jobattrs:
                pp["job-attributes-tag"] = jobattrs
            _LOGGER.debug(
                "Sending print job with op attributes %s and job attributes %s",
                opattrs,
                jobattrs,
            )
            result = await ipp.execute(
                pyipp.enums.IppOperation.PRINT_JOB,
                pp,
            )
        except (
            pyipp.exceptions.IPPConnectionError,
            pyipp.exceptions.IPPParseError,
            pyipp.exceptions.IPPResponseError,
            pyipp.exceptions.IPPVersionNotSupportedError,
        ):
            raise
        except pyipp.exceptions.IPPError as e:
            if len(e.args) > 1:
                try:
                    error_code_enum = pyipp.enums.IppStatus(e.args[1]["status-code"])
                    raise HomeAssistantError(
                        "Printer rejected the print job, responding with status code %r"
                        % (error_code_enum,)
                    )
                except ValueError:
                    raise e
            else:
                raise
        finally:
            # Undo monkey-patching.
            ATTRIBUTE_TAG_MAP["media"] = saved_media_tag

        return munge_jobs(result["jobs"])[0]


async def get_printer_information_helper(
    hass: HomeAssistant,
    conf: IPPConfigEntry,
    get_incomplete_jobs: bool,
    get_complete_jobs: bool,
) -> tuple[JsonValueType, list[JsonValueType]]:
    async with pyipp.IPP(
        host=conf.data[CONF_HOST],
        port=conf.data[CONF_PORT],
        base_path=conf.data[CONF_BASE_PATH],
        tls=conf.data[CONF_SSL],
        verify_ssl=conf.data[CONF_VERIFY_SSL],
        session=async_get_clientsession(hass, conf.data[CONF_VERIFY_SSL]),
    ) as ipp:
        opattr = {
            "requested-attributes": pyipp.const.DEFAULT_PRINTER_ATTRIBUTES
            + [
                "document-format-supported",
                "printer-resolution-supported",
                "print-scaling-supported",
                "print-quality-supported",
                "media-size-supported",
                "media-supported",
                "media-col-database",
                "media-ready",
                "media-col-ready",
            ],
        }
        _LOGGER.debug("Sending query job with attributes %s", opattr)

        printer_resp = await ipp.execute(
            pyipp.enums.IppOperation.GET_PRINTER_ATTRIBUTES,
            {
                "operation-attributes-tag": opattr,
            },
        )
        printer = cast(
            dict[str, JsonValueType],
            printer_resp["printers"][0] if printer_resp["printers"] else {},
        )
        if "print-quality-supported" in printer:
            try:
                printer["print-quality-supported"] = [
                    c.name.lower()
                    for c in cast(
                        list[pyipp.enums.IppPrintQuality],
                        printer["print-quality-supported"],
                    )
                ]
            except Exception:
                pass
        complete_jobs_blob = (
            await ipp.execute(
                pyipp.enums.IppOperation.GET_JOBS,
                {
                    "operation-attributes-tag": {
                        "requested-attributes": pyipp.const.DEFAULT_JOB_ATTRIBUTES,
                        "which-jobs": "completed",
                    },
                },
            )
            if get_complete_jobs
            else {}
        )
        incomplete_jobs_blob = (
            await ipp.execute(
                pyipp.enums.IppOperation.GET_JOBS,
                {
                    "operation-attributes-tag": {
                        "requested-attributes": pyipp.const.DEFAULT_JOB_ATTRIBUTES,
                        "which-jobs": "not-completed",
                    },
                },
            )
            if get_incomplete_jobs
            else {}
        )
        jobs: list[dict[str, JsonValueType]] = complete_jobs_blob.get(
            "jobs", []
        ) + incomplete_jobs_blob.get("jobs", [])
        jobs = list(
            sorted(
                jobs,
                key=lambda job: job["job-id"] if isinstance(job["job-id"], int) else 0,
            )
        )
        jobs = munge_jobs(jobs)

    return printer, cast(list[JsonValueType], jobs)


@callback
def async_get_device_from_entity_id(
    hass: HomeAssistant,
    entity_id: str,
    ent_reg: er.EntityRegistry | None = None,
    dev_reg: dr.DeviceRegistry | None = None,
) -> str:
    """Get node from an entity ID.

    Raises ValueError if entity is invalid.
    """
    if not ent_reg:
        ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)

    if entity_entry is None or entity_entry.platform != IPP_DOMAIN:
        raise ValueError(f"Entity {entity_id} is not a valid {IPP_DOMAIN} entity")

    # Assert for mypy, safe because we know that zwave_js entities are always
    # tied to a device
    assert entity_entry.device_id
    return entity_entry.device_id


@callback
def async_get_devices_from_area_id(
    hass: HomeAssistant,
    area_id: str,
    ent_reg: er.EntityRegistry | None = None,
    dev_reg: dr.DeviceRegistry | None = None,
) -> set[str]:
    """Get nodes for all Z-Wave JS devices and entities that are in an area."""
    devices: set[str] = set()
    if ent_reg is None:
        ent_reg = er.async_get(hass)
    if dev_reg is None:
        dev_reg = dr.async_get(hass)
    # Add devices for all entities in an area that are IPP entities
    devices.update(
        {
            entity.device_id
            for entity in er.async_entries_for_area(ent_reg, area_id)
            if entity.platform == IPP_DOMAIN and entity.device_id is not None
        }
    )
    # Add devices in an area that are IPP devices
    devices.update(
        device.id
        for device in dr.async_entries_for_area(dev_reg, area_id)
        if any(
            cast(
                IPPConfigEntry,
                hass.config_entries.async_get_entry(config_entry_id),
            ).domain
            == IPP_DOMAIN
            for config_entry_id in device.config_entries
        )
    )

    return devices


@callback
def async_get_devices_from_targets(
    hass: HomeAssistant,
    val: dict[str, Any],
    ent_reg: er.EntityRegistry | None = None,
    dev_reg: dr.DeviceRegistry | None = None,
    logger: logging.Logger = _LOGGER,
) -> set[str]:
    """Get devices for all targets.

    Supports entity_id with group expansion, area_id, and device_id.
    """
    devices: set[str] = set()
    # Convert all entity IDs to nodes
    for entity_id in expand_entity_ids(hass, val.get(ATTR_ENTITY_ID, [])):
        try:
            devices.add(
                async_get_device_from_entity_id(hass, entity_id, ent_reg, dev_reg)
            )
        except ValueError as err:
            logger.warning(err.args[0])

    # Convert all area IDs to nodes
    for area_id in val.get(ATTR_AREA_ID, []):
        devices.update(async_get_devices_from_area_id(hass, area_id, ent_reg, dev_reg))

    # Convert all device IDs to nodes
    for device_id in val.get(ATTR_DEVICE_ID, []):
        try:
            devices.add(device_id)
        except ValueError as err:
            logger.warning(err.args[0])

    return devices


def get_device_id(hass: HomeAssistant, call: ServiceCall) -> str:
    device_id = list(async_get_devices_from_targets(hass, call.data))
    if len(device_id) != 1:
        raise ServiceValidationError("only a single device is supported at a time")
    return device_id[0]
