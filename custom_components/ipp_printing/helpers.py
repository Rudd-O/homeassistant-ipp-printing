"""IPP printing integration services."""

import pyipp
import pyipp.enums
import pyipp.const

from typing import cast
from homeassistant.core import HomeAssistant

from homeassistant.util.json import JsonValueType
from homeassistant.components.ipp.coordinator import IPPConfigEntry
from homeassistant.components.ipp.const import CONF_BASE_PATH
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession


def munge_jobs(jobs: list[dict[str, JsonValueType]]) -> list[dict[str, JsonValueType]]:
    new_jobs = []
    for job in jobs:
        job = job.copy()
        job_state: int = cast(int, job["job-state"])
        state_enum = pyipp.enums.IppJobState(job_state).name.lower()
        job["job-state"] = state_enum
        new_jobs.append(job)
    return new_jobs


async def print_to_ipp(
    hass: HomeAssistant, conf: IPPConfigEntry, data: bytes, mimetype: str
) -> dict[str, JsonValueType]:
    async with pyipp.IPP(
        host=conf.data[CONF_HOST],
        port=conf.data[CONF_PORT],
        base_path=conf.data[CONF_BASE_PATH],
        tls=conf.data[CONF_SSL],
        verify_ssl=conf.data[CONF_VERIFY_SSL],
        session=async_get_clientsession(hass, conf.data[CONF_VERIFY_SSL]),
    ) as ipp:
        result = await ipp.execute(
            pyipp.enums.IppOperation.PRINT_JOB,
            {
                "operation-attributes-tag": {
                    "document-format": mimetype,
                },
                "data": data,
            },
        )
        return munge_jobs(result["jobs"])[0]


async def get_printer_information_helper(
    hass: HomeAssistant,
    conf: IPPConfigEntry,
    get_incomplete_jobs: bool,
    get_complete_jobs: bool,
) -> tuple[pyipp.Printer, list[JsonValueType]]:
    async with pyipp.IPP(
        host=conf.data[CONF_HOST],
        port=conf.data[CONF_PORT],
        base_path=conf.data[CONF_BASE_PATH],
        tls=conf.data[CONF_SSL],
        verify_ssl=conf.data[CONF_VERIFY_SSL],
        session=async_get_clientsession(hass, conf.data[CONF_VERIFY_SSL]),
    ) as ipp:
        printer = await ipp.printer()
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
