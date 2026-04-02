# Short snippet of code that allows me to test the printer.

import sys
import logging
import asyncio
import pyipp
import pyipp.enums
from pyipp.enums import IppTag
from typing import Any


async def main(fname: str) -> None:
    logging.basicConfig(level=logging.DEBUG)
    async with pyipp.IPP(
        host="10.250.1.47",
        port=631,
        base_path="/printers/Dymo_LabelWriter_550_Turbo",
        tls=False,
        verify_ssl=True,
    ) as ipp:
        print(await ipp.printer())
        opattrs: dict[str, Any] = {"document-format": "application/pdf"}
        jobattrs: dict[str, Any] = {}
        # Requires forked python-ipp.
        # jobattrs["media-col"] = {
        #    "media-size": {
        #        "x-dimension": IppAttribute(IppTag.INTEGER, 8890),
        #        "y-dimension": IppAttribute(IppTag.INTEGER, 3560),
        #    },
        # }
        # jobattrs["page-top"] = 0
        jobattrs["print-scaling"] = "none"

        pp = {
            "operation-attributes-tag": opattrs,
            "job-attributes-tag": jobattrs,
            "data": open(
                fname,
                "rb",
            ).read(),
        }
        print(
            await ipp.execute(
                pyipp.enums.IppOperation.PRINT_JOB,
                pp,
            )
        )


loop = asyncio.get_event_loop()
loop.run_until_complete(main(sys.argv[1]))
