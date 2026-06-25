import re
from enum import IntEnum
from os import path

from sardana.pool import AcqSynch
from sardana.pool.controller import (
    DefaultValue,
    Description,
    FGet,
    FSet,
    Referable,
    TwoDController,
    Type,
)
from tango import DeviceProxy

ALLOWED_SYNCHRONIZATIONS = [AcqSynch.SoftwareTrigger, AcqSynch.SoftwareStart]


class Gain(IntEnum):
    LOW = 0
    STD = 1
    HDR = 2
    HDR_LOWNOISE = 3


class GreateyesTangoTwoDController(TwoDController, Referable):
    """TwoDController for Greateyes CHARLIE sCMOS camera tango device server."""

    ctrl_properties = {
        "tangoFQDN": {
            Type: str,
            Description: "The FQDN of the greateyes tango DS",
            DefaultValue: "greateyes.hhg.lab",
        },
    }

    axis_attributes = {
        "SavingEnabled": {
            Type: bool,
            FGet: "isSavingEnabled",
            FSet: "setSavingEnabled",
            Description: "Enable/ disable saving of images in tiff files."
        },
        "Gain": {
            Type: str,
            FGet: "getGain",
            FSet: "setGain",
            Description: "Gain mode (LOW, STD, HDR, HDR_LOWNOISE)",
        },
    }

    MaxDevice = 1

    def __init__(self, inst, props, *args, **kwargs):
        """Constructor"""
        super().__init__(inst, props, *args, **kwargs)
        self._last_image_returned: int = 0
        self._synchronization = AcqSynch.SoftwareTrigger
        self.proxy = DeviceProxy(self.tangoFQDN)

    def getLastFileIndex(self) -> int:
        """
        Get the index of the last saved file.

        This is a dirty workaround since the greateyes tangoDS
        does not provide an image counter.
        """
        index = re.findall(r"([0-9]+)\.tif", self.proxy.LastSavedImage)
        if len(index):
            return int(index[0])
        else:
            return 0

    def getFileNamePattern(self) -> str:
        return path.join(self.proxy.FileDir, f"{self.proxy.FilePrefix}%06d.tif")

    def ReadOne(self, axis):
        if self._synchronization == AcqSynch.SoftwareTrigger:
            return self.proxy.Image
        elif self._synchronization == AcqSynch.SoftwareStart:
            raise ValueError(
                "value_ref_enabled is required for SoftwareStart synchronization!"
            )

    def RefOne(self, axis):
        """
        Return the file uri of the last saved image(s).

        
        """
        if not self.proxy.SaveImageFiles:
            raise ValueError("value_ref_enabled but file saving is off!")

        if self._synchronization == AcqSynch.SoftwareTrigger:
            return self.proxy.LastSavedImage

        elif self._synchronization == AcqSynch.SoftwareStart:
            current_index = self.getLastFileIndex()
            filepattern = self.getFileNamePattern()
            new_indices = range(self._last_image_returned, current_index)
            self._last_image_returned = current_index
            list_new_files = [filepattern % (i + 1) for i in new_indices]
            return list_new_files

        else:
            raise NotImplementedError("Only Software synchronization implemented!")

    def SetCtrlPar(self, name, value):
        super().SetCtrlPar(name, value)
        name = name.lower()
        if name == "synchronization":
            if value not in ALLOWED_SYNCHRONIZATIONS:
                raise ValueError("Only Software synchronzation implemented!")
            else:
                self._synchronization = value
            
    def SetAxisPar(self, axis, parameter, value):
        parameter = parameter.lower()
        if parameter == "value_ref_pattern":
            folder, fname = path.split(value)
            if not path.isdir(folder):
                raise ValueError(f"{folder} is not a directory!")
            self.proxy.FileDir = folder
            self.proxy.FilePrefix = fname
            self.proxy.FileStartNum = 1
        elif parameter == "value_ref_enabled" and not value:
            raise ValueError("Cannot disable value_ref_enabled on 2D")
        else:
            return super().SetAxisPar(axis, parameter, value)

    def GetAxisPar(self, axis, parameter):
        parameter = parameter.lower()
        if parameter == "value_ref_pattern":
            return self.getFileNamePattern()
        elif parameter == "value_ref_enabled":
            return True
        elif parameter == "shape":
            return [self.proxy.RoiXWidth, self.proxy.RoiYHeight]

    def StateOne(self, axis):
        """Get the specified counter state"""
        return self.proxy.State()

    def PrepareOne(self, axis, value, repetitions, latency, nb_starts):
        """Set exposure time and number of acquisitions."""
        self.proxy.ExposureTime = 1000 * value
        if repetitions > 1:
            self.proxy.ReadoutMode = 1
            self.proxy.NumAcquisitions = repetitions
        else:
            self.proxy.ReadoutMode = 0
        self.proxy.PrepareAcq()

    def StartOne(self, axis, value=None):
        """acquire the specified counter"""
        self._last_image_returned = self.getLastFileIndex()
        print(f"CHARLIE last index: {self._last_image_returned}")
        self.proxy.StartAcq()
        return

    def StopOne(self, axis):
        """Stop the specified counter"""
        self.proxy.StopAcq()

    def AbortOne(self, axis):
        """Abort the specified counter"""
        self.proxy.StopAcq()

    def isSavingEnabled(self, axis=None):
        """Return whether file saving is enabled on the tango DS."""
        return bool(self.proxy.SaveImageFiles)

    def setSavingEnabled(self, axis, value):
        """Enable or Disable file saving."""
        self.proxy.SaveImageFiles = bool(value)

    def getGain(self) -> str:
        """Return the current detetor gain string."""
        return self.proxy.Gain.name

    def setGain(self, value: str):
        """Sets the detector gain mode.

        Valid modes are: LOW, STD, HDR, HDR_LOWNOISE
        """

        value = Gain(value) if isinstance(value, int) else Gain[value]
        self.proxy.Gain = value

