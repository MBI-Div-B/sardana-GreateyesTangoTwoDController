import copy
import os
import pprint

from sardana.macroserver.macro import Macro, Optional, Type

CHARLIE_ENV = "_CharlieConfiguration"


def get_env(macro_obj, var=CHARLIE_ENV):
    """Get a macroserver environment variable.

    Defaults to _CharlieConfiguration.
    """
    try:
        conf = copy.deepcopy(macro_obj.getEnv(var))
    except Exception:
        raise ValueError("Environment variable not found in environment!")
    return conf


def make_image_folder(macro_obj):
    """Create new image subfolder based on next scanId in configured base folder."""
    scanId = get_env(macro_obj, "ScanID")
    charlie_conf = get_env(macro_obj)
    image_folder = os.path.join(charlie_conf["folder"], f"scan_{scanId:06d}")
    if not os.path.exists(image_folder):
        os.mkdir(image_folder)
    return image_folder


class charlie_conf(Macro):
    """Show and alter current CHARLIE configuration."""

    param_def = [
        ["parameter", Type.String, Optional, "Parameter to set or query."],
        ["value", Type.String, Optional, "Value to set (optional)."],
    ]

    def run(self, parameter=None, value=None):
        try:
            charlie_conf = get_env(self)
        except ValueError:
            self.output("No CHARLIE configuration found. Creating default one.")
            charlie_conf = {
                "folder": get_env(self, "ScanDir"),
                "channel": "charlie",
                "basename": "charlie",
            }
            self.setEnv(CHARLIE_ENV, charlie_conf)
        if parameter is None:
            # no parameter given -> print full config
            self.print_config(charlie_conf)
        elif value is None:
            # parameter given, but no value -> output parameter value
            self.print_config(charlie_conf, parameter)
        else:
            # both parameter and value given -> set parameter
            # TODO: validate parameters!
            charlie_conf[parameter] = value
            self.setEnv(CHARLIE_ENV, charlie_conf)

    def print_config(self, conf, parameter=None):
        if parameter is None:
            self.output(pprint.pformat(conf, width=16))
        else:
            self.output(f"{parameter} = {conf[parameter]}")


class charlie_hook(Macro):
    """Configure CHARLIE detector before scan."""

    def run(self):
        conf = get_env(self)
        mg_active = self.getEnv("ActiveMntGrp")
        mg = self.getMeasurementGroup(mg_active)

        for channel in mg.getChannelLabels():
            if channel != conf["channel"]:
                continue

            folder = make_image_folder(self)
            file_pattern = os.path.join(folder, f"{conf['basename']}_")
            self.set_meas_conf("ValueRefPattern", file_pattern, channel, mg)
            self.set_meas_conf("ValueRefEnabled", True, channel, mg)




