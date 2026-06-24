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
        self._initialized: bool = False
        self._last_image_returned: int = 0
        self._synchronization = AcqSynch.SoftwareTrigger

        try:
            self.proxy = DeviceProxy(self.tangoFQDN)
            self._initialized = True
        except Exception as exc:
            self._log.error(f"Error starting GreateyesTangoTwoDController: {exc}")

    def getLastFileIndex(self) -> int:
        index = re.findall(r"([0-9]+)\.tif", self.proxy.LastSavedImage)
        if len(index):
            return index[0]
        else:
            return 0

    def getFileNamePattern(self) -> str:
        return path.join(self.proxy.FileDir, f"{self.proxy.FilePrefix}%06d.tif")

    def RefOne(self, axis):
        if not self.proxy.SaveImageFile:
            return "None"

        elif self._synchronization == AcqSynch.SoftwareTrigger:
            return self.proxy.LastSavedImage

        elif self._synchronization == AcqSynch.SoftwareStart:
            current_index = self.getLastFileIndex()
            filepattern = self.getFileNamePattern()
            new_indices = range(self._last_image_returned, current_index)
            self._last_image_returned = current_index
            return [filepattern % i for i in new_indices]

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
        self.proxy.ExposureTime = 1000 * value
        if repetitions > 1:
            self.proxy.ReadoutMode = 1
            self.proxy.NumAcquisitions = repetitions
        else:
            self.proxy.ReadoutMode = 0
        self.proxy.PrepareAcq()

    def LoadOne(self, axis, value, repetitions, latency):
        pass

    def StartOne(self, axis, value=None):
        """acquire the specified counter"""
        self.proxy.StartAcq()
        return

    def StopOne(self, axis):
        """Stop the specified counter"""
        self.proxy.StopAcq()

    def AbortOne(self, axis):
        """Abort the specified counter"""
        self.proxy.StopAcq()

    def isSavingEnabled(self, axis=None):
        return bool(self.proxy.SaveImageFiles)

    def setSavingEnabled(self, axis, value):
        self.proxy.SaveImageFiles = bool(value)

    def getGain(self) -> str:
        return self.proxy.Gain.name.upper()

    def setGain(self, value: str):
        self.proxy.Gain = Gain[value.upper()]





