# Short snippet of code that allows me to test the printer.

import logging
import asyncio
import pyipp
import pyipp.enums
from pyipp.enums import IppTag
from pyipp.serializer import IppAttribute
from typing import Any


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    async with pyipp.IPP(
        host="localhost",
        port=631,
        base_path="/printers/Cups-PDF",
        tls=False,
        verify_ssl=True,
    ) as ipp:
        print(await ipp.printer())
        opattrs: dict[str, Any] = {"document-format": "text/plain"}
        jobattrs: dict[str, Any] = {}
        # if paper_size is not None: FIXME UNCOMMENT
        #    jobattrs["media"] = paper_size
        jobattrs["media-col"] = {
            "media-size": {
                "x-dimension": IppAttribute(IppTag.INTEGER, 21590),  # ; US Letter Width
                "y-dimension": IppAttribute(
                    IppTag.INTEGER, 27940
                ),  # ; US Letter Length
            },
            "media-top-margin": IppAttribute(IppTag.INTEGER, 500),
            # "media-right-margin": IppAttribute(IppTag.INTEGER, 1270),
            # "media-top-margin": IppAttribute(IppTag.INTEGER, 1270),
            # "media-bottom-margin": IppAttribute(IppTag.INTEGER, 1270),
        }
        jobattrs["print-scaling"] = IppAttribute(IppTag.KEYWORD, "none")
        jobattrs["media-left-margin"] = (IppAttribute(IppTag.INTEGER, 72),)
        # jobattrs["page-left"] = IppAttribute(
        #     IppTag.INTEGER,
        #     72,
        # )

        pp = {
            "operation-attributes-tag": opattrs,
            "job-attributes-tag": jobattrs,
            "data": "hello world!".encode(
                "utf-8"
            ),  # open("/home/user/Downloads/testpage.jpg", "rb").read(),
        }
        print(
            await ipp.execute(
                pyipp.enums.IppOperation.PRINT_JOB,
                pp,
            )
        )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
