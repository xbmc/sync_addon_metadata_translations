## Sync Add-on Metadata Translations

With this tool you can sync a Kodi add-on's metadata (`Summary`, `Description`, and `Disclaimer`) translations between the addon.xml and related po files.

### Installation

- `pip install git+https://github.com/xbmc/sync_addon_metadata_translations.git`
  
or 

- `git clone https://github.com/anxdpanic/sync_addon_metadata_translations`

- `cd <path-to-cloned-repo>`

- `pip install .`

### Usage
```
sync-addon-metadata-translations [-h] [-ptx] [-xtp] [-path [PATH]] [-multi]

optional arguments:
  -h, --help                    show this help message and exit
  -ptx, --po-to-xml             sync po file values to the addon.xml file
  -xtp, --xml-to-po             sync addon.xml values to all po files
  -path [PATH], --path [PATH]   working directory
  -multi, --multiple-addons     multiple add-ons in the working directory
```
