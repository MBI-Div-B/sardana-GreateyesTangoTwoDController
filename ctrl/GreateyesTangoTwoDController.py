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

ALLOWED_SYNCHRONIZATIONS = [AcqSynch.SoftwareTrigger,]


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
            Description: "Enable/ disable saving of images in tiff files.",
        },
        "Gain": {
            Type: str,
            FGet: "getGain",
            FSet: "setGain",
            Description: "Gain mode (LOW, STD, HDR, HDR_LOWNOISE)",
        },
        "Nframes": {
            Type: int,
            FGet: "getNframes",
            FSet: "setNframes",
            Description: "Number of frames to acquire for a single acquisition.",
        },
    }

    MaxDevice = 1

    def __init__(self, inst, props, *args, **kwargs):
        """Constructor"""
        super().__init__(inst, props, *args, **kwargs)
        self._start_index: int = 0
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
        return self.proxy.Image

    def RefOne(self, axis):
        """
        Return the file uri of the last saved image(s).

        In case of multi-frame acquisitions, the folder and index range is returned.
        """
        if not self.proxy.SaveImageFiles:
            raise ValueError("value_ref_enabled but file saving is off!")

        readoutmode = self.proxy.ReadoutMode
        if readoutmode == 0:
            return f"file://{self.proxy.LastSavedImage}"
        elif readoutmode == 1:
            first_index = self._start_index
            last_index = first_index + self.proxy.NumAcquisitions
            filepattern = self.getFileNamePattern()
            return f"file://{filepattern};;{first_index},{last_index}"
        else:
            raise ValueError("Detector is in video mode!")

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
        else:
            print(f"SetAxisPar {axis}, {parameter}, {value}")

    def GetAxisPar(self, axis, parameter):
        print(f"GetAxisPar {axis}, {parameter}")
        parameter = parameter.lower()
        if parameter == "value_ref_pattern":
            return self.getFileNamePattern()
        elif parameter == "value_ref_enabled":
            return True
        elif parameter == "shape":
            return [self.proxy.RoiXWidth, self.proxy.RoiYHeight]
        else:
            return super().GetAxisPar(axis, parameter)

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
        self._start_index = self.getLastFileIndex()
        print(f"CHARLIE last index: {self._start_index}")
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

    def getGain(self, axis) -> str:
        """Return the current detetor gain string."""
        return self.proxy.Gain.name

    def setGain(self, axis, value: str):
        """Sets the detector gain mode.

        Valid modes are: LOW, STD, HDR, HDR_LOWNOISE
        """

        value = Gain(value) if isinstance(value, int) else Gain[value]
        self.proxy.Gain = value

    def getNframes(self, axis) -> int:
        """Get number of frames to acquire."""
        return self.proxy.NumAcquisitions

    def setNframes(self, axis, value: int):
        """Set number of frames to acquire and according readout mode."""
        if value <= 0:
            raise ValueError("Nmber of frames needs to be positive.")
        elif value == 1:
            self.proxy.ReadoutMode = 0
        else:
            self.proxy.ReadoutMode = 1
            self.proxy.NumAcquisitions = value


