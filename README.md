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

This may seem trivial, especially if you have no source of data to print
— but there is.  Check out the
[Simple image raster integration](https://github.com/Rudd-O/hass-simple-image-raster)
for Home Assistant to generate images on the fly, and combine it with this
extension to print anything you want, through automations and scripts.
In particular, check out [the examples](https://github.com/Rudd-O/hass-simple-image-raster/tree/master/examples)
to see what you can do with this combination of integrations.

See *Installation* below for how to set it up before attempting to use it.

## How to use this

From the following instructions you should be able to deduce that you can enable
automations (e.g. via REST triggers) and scripts in Home Assistant to print
any document in any format, so long as the document format is supported by your
printer.

### Printing plain text

If your printer supports plain text, simply:

* Navigate to *Developer tools* tab *Actions* and select the `Print` action.
* Select your printer.
* Enable the *Text* field and type in your text.
* Hit the *Perform action* button.

### Printing other document formats supported by your printer

If your printer supports other formats, such as TIFF / JPEG images, PDF or
PostScript, follow these instructions.

Base-64 encode a document in a format supported by your printer:

```sh
base64 < little-image.png > little-image.txt
# little-image.txt contains the encoded file
```

Yes, we hate that you have to Base-64 encode data in order to print it, but
actions in Home Assistant simply do not support binary data.  It's a platform
limitation that we can do nothing about.

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

### What document formats can I print in?  What options does my printer support

Ask your printer!  Use the action `ipp_printer.get_printer_information`.

For example: document formats can be found by looking at the field
`document-format-supported` inside the `printer` field of the response.  Paper
sizes are listed under attribute `media-supported`.  And so on, and so forth.

*Pro tip:* if your printer is a CUPS backend, it's almost certainly going to
support a wide variety of documents, including images and PDFs.

## Examples

### Prevent your printer's nozzles from drying out

If an inkjet printer goes unused for a while, it often happens that the
nozzles of the printer dry out hard, and it is (sometimes) not possible
to recover from this situation.

Printing regularly prevents this problem.

Here is a Home Assistant automation that will print a page every second
Sunday of the month, in color.  At the cost of 26 pages per year, with
very little color use, you'll prevent damage to your printer without ever
having to think about it.

Note that you must change the device to your own IPP device before you
save the automation.  This automation also assumes that your printer
can print RGB JPEG images.

```yaml
alias: Print a test page
description: Runs every other week to prevent the nozzles of the printer from drying out.
triggers:
  - trigger: time
    at: "15:00:00"
    weekday:
      - sun
conditions:
  - condition: template
    value_template: "{{ now().isocalendar().week % 2 == 0 }}{# only biweekly #}"
    alias: Every other week
actions:
  - action: ipp_printing.print
    metadata: {}
    target:
      device_id:
        - 7525b30367e90d1fad7cf4f9c734116a
    data:
      data: >-
        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
        AAAAAAAAAAAAAAAAAAAAAAAP/9k=
      mimetype: image/jpeg
mode: single
```

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
