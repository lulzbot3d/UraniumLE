# Copyright (c) 2023 UltiMaker
# Uranium is released under the terms of the LGPLv3 or higher.

import os

from UM.Application import Application
from UM.Preferences import Preferences
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from .LocalFileOutputDevice import LocalFileOutputDevice

from UM.i18n import i18nCatalog
catalog = i18nCatalog("uranium")


##  Implements an OutputDevicePlugin that provides a single instance of LocalFileOutputDevice
class LocalFileOutputDevicePlugin(OutputDevicePlugin):
    def __init__(self):
        super().__init__()

        Application.getInstance().getPreferences().addPreference("local_file/last_used_type", "")
        Application.getInstance().getPreferences().addPreference("local_file/dialog_save_path",
                                                                 os.path.expanduser("~/"))

    def start(self):
        self.getOutputDeviceManager().addProjectOutputDevice(LocalFileOutputDevice(add_to_output_devices = True))

    def stop(self):
        self.getOutputDeviceManager().removeProjectOutputDevice("local_file")
