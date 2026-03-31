# IPP printing for Home Assistant

If you have added at least one IPP printer to Home assistant, this integration
adds two new actions to your printers you can call:

1. `ipp_printer.print`: Sends a print job to the printer.  Select your printer
   device, add a base64-encoded blob of data, and add the MIME type that
   describes your data (before encoding) best.  Returns the information
   on the job sent to the printer.
2. `ipp_printer.get_printer_information`: Gets information on the printer.
   Select your printer device, and optionally select which kinds of jobs
   you would like information on.  The returned data lists basic printer
   information and the status of all known jobs.

## Installation

1. Install this integration with HACS (adding repository required), or copy the contents of this
   repository into the `custom_components/ipp_printer` directory.
2. Restart Home Assistant.
3. Be sure you have already added at least one IPP printer to Home assistant using the
   IPP integration that ships with Home Assistant.
3. Go to **Settings** → **Integrations** and add integration **IPP printer**.

That's it.  The actions should now be available from Developer tools and
in the script and automation editors as well.
