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

See *Installation* below for how to set it up before attempting to use it.

## How to use this

Base-64 encode a document in a format supported by your printer:

```sh
base64 < little-image.png > little-image.txt
# little-image.txt contains the encoded file
```

Get the MIME type of the original file:

```sh
file -i little-image.png
# shall output the MIME type
```

Open the resulting file into a text editor, and copy it to your clipboard.

Navigate to *Developer tools* tab *Actions* and select the `Print` action.

Select your printer.

In the *Data* field, paste the contents of what you copied.  In the *MIME type*
field, place the MIME type you obtained (ignore anything after the semicolon
if your MIME type output shows that).

Hit the *Perform action* button.

From these instructions you should be able to deduce that you can enable
automations (e.g. via REST triggers) and scripts in Home Assistant to print
any document in any format, so long as the document format is supported by your
printer.

### What document formats can I print in?  What options does my printer support

Ask your printer!  Use the service `ipp_printer.get_printer_information`.

For example: document formats can be found by looking at the field
`document-format-supported` inside the `printer` field of the response.  Paper
sizes are listed under attribute `media-supported`.  And so on, and so forth.

*Pro tip:* if your printer is a CUPS backend, it's almost certainly going to
support a wide variety of documents, including images and PDFs.

## Installation

1. Install this integration with HACS (add this repository as an integration type
   repository to HACS).  Alternatively (not recommended), copy the
   `custom_components/ipp_printer` directory of this repository into your Home Assistant's configuration `custom_components` directory.
2. Restart Home Assistant..
3. Be sure you have already added at least one IPP printer to Home assistant using the
   IPP integration that ships with Home Assistant.
4. Go to **Settings** → **Integrations** and add integration **IPP printer**.
5. Confirm the dialog onscreen.

That's it.  The actions should now be available from Developer tools and
in the script and automation editors as well.

## Legal

This code is distributed as-is under the MIT license.
