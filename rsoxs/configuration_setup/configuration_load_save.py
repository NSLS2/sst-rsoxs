## New spreadsheet loader and saver

import os
import numpy as np
import pandas as pd
import ast
import copy
import json
import datetime
import re, warnings, httpx
import uuid


from nbs_bl.devices.sampleholders import SampleHolderBase
from nbs_bl.hw import manipulator

from ..plans.default_energy_parameters import energyListParameters

from .configuration_load_save_sanitize import (
    load_configuration_spreadsheet_local, 
    save_configuration_spreadsheet_local,
    get_sample_dictionary_nbs_format_from_rsoxs_config,
)
from ..redis_config import rsoxs_config




def load_sheet(file_path):
    """
    Loads spreadsheet and updates sample configuration in RSoXS control computer.
    """    

    ## Update rsoxs_config, used in rsoxs codebase
    configuration = load_configuration_spreadsheet_local(file_path=file_path)
    rsoxs_config["bar"] = copy.deepcopy(configuration)
    print("Replaced persistent configuration with configuration loaded from file path: " + str(file_path))

    ## Sync nbs manipulator object
    try:
        samples_dictionary_nbs_format = get_sample_dictionary_nbs_format_from_rsoxs_config(configuration=copy.deepcopy(rsoxs_config["bar"]))
        manipulator.load_sample_dict(samples_dictionary_nbs_format)
    except:
        ## Before picking sample locations from bar image, the spreadsheet does not have sample locations.
        ## Workaround for now is to pass until a spreadsheet with sample locations is loaded.
        ## TODO: There is still an issue that an entire sample dictionary will not get sync'ed if a single sample does not have coordinates.  It would be good to remove that single sample rather than not sync the entire sample list.
        print("At least one sample does not have location coordinates.  Reload sheet after coordinates are added to sync with nbs-bl.")
        pass
    
    return

def save_sheet(file_path, file_label):
    ## Test comment + more comment
    save_configuration_spreadsheet_local(configuration=rsoxs_config["bar"], file_path=file_path, file_label=file_label)
    return








