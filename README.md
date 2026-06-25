# sardana-GreateyesTangoTwoDController
Sardana TwoDController for Greateyes Tango device server.

This controller is written for the CHARLIE sCMOS tango-ds v0.1


## How to add controller and expchannel

In spock

```
defctrl GreateyesTangoTwoDController gecharliectrl tangoFQDN <GE_TANGO_DEVICE>
defelem charlie gecharliectrl
```

## Features and Usage

### General

The controller is intended to be used in **SoftwareTrigger** synchronization **with file referencing enabled**.
Directly returning the image data into sardana causes a lot of overhead and is greatly discouraged.

```
Door_maxi_1 [1]: get_meas_conf advanced
ActiveMntGrp = mg_charlie
   Channel   Enabled   Output   PlotType   PlotAxes     Timer   Monitor   Synchronizer   Synchronization   ValueRefEnabled   ValueRefPattern
 --------- --------- -------- ---------- ---------- --------- --------- -------------- ----------------- ----------------- -----------------
   charlie      True     True         No        n/a   charlie   charlie       software           Trigger              True   <truncated>
```

### Hook Macros

The macros in `charlie_macros.py` are intended to facilitate efficient and consistent behavior. `charlie_hook` should be registered as pre-scan hook:

`defgh charlie_hook pre-scan`

The hook will configure file saving for the next scan according to environment variables set via the `charlie_conf` macro:

```
Door_maxi_1 [4]: charlie_conf
{'basename': '2606_OPUS',
 'channel': 'charlie',
 'nframes': 10,
 'create_folders': True,
 'folder': '/home/labuser/data/2606_BESSY_UE51PGM/gecmos',
 'scansubfolder': True}
```

The parameters can be configured with the same macro:

`charlie_conf basename 2606_exp1_`

| Parameter | Description
|-----------|------------
| channel   | name of the CHARLIE sardana 2Dexpchannel
| nframes   | number of frames to acquire for each software trigger
| folder    | base data folder
| basename  | tif file name part before the counting index
| scansubfolder  | If True, each scan will create a new subfolder
| create_folders | If True, the hook macro creates the folder for the tango DS to write files into


To automatically disable file saving when not in a proper scan, register the `charlie_disable_saving` macro post-scan. This is useful to not clutter the file system with `ct`s.


### Multiple Acquisition

To acquire multiple frames per scan point, set the `nframes` configuration parameter:

`charlie_conf nframes 20`

If set to a value greater than one, multiple images will be recorded for each SoftwareTrigger. The names of the files saved will be returned as file references in the form:

`file://<folder>[/<subfolder>]/<basename>_%06d.tif;<start_index>,<end_index>`

Example for a scan point with 10 acquisitions:

`file:///home/labuser/data/2606_BESSY_UE51PGM/gecmos/scan_001335/2606_OPUS_%06d.tif;407-416`

