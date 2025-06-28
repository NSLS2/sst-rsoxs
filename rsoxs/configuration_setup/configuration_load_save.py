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
#from nbs_bl.hw import manipulator ## 20250627 - For some reason, this throws an error even though devices can be imported fine in other files?  Possibly a circular import issue?

from ..plans.default_energy_parameters import energyListParameters

from .configuration_load_save_sanitize import load_configuration_spreadsheet_local, save_configuration_spreadsheet_local
from ..redis_config import rsoxs_config




def load_sheet(file_path):
    """
    Loads spreadsheet and updates sample configuration in RSoXS control computer.
    """    

    ## Update rsoxs_config, used in rsoxs codebase
    configuration = load_configuration_spreadsheet_local(file_path=file_path)
    rsoxs_config["bar"] = copy.deepcopy(configuration)
    print("Replaced persistent configuration with configuration loaded from file path: " + str(file_path))

    ## TODO: Uncomment items below after import errors get resolved.
    ## But larger issue is that there needs to be a way to keep nbs-bl's sample list in sync with rsoxs_config throughout the codebase, not just when loading a spreadsheet.
    ## Otherwise, if a spreadsheet is not explicitly loaded, any other changes will not get reflected, and move_sample will not work consistently and reliably.
    ## Update nbs-bl's sample list
    """
    try: manipulator.load_sample_file(filename=file_path)
    except: 
        ## Before picking sample locations from bar image, the spreadsheet does not have sample locations.
        ## Workaround for now is to pass until a spreadsheet with sample locations is loaded.
        ## Unfortunately, this requires manually loading spreadsheet before scans can be run.
        ## TODO: find better fix to keep nbs-bl's sample list sync'ed with rsoxs_config.
        print("At least one sample does not have location coordinates.  Reload sheet after coordinates are added to sync with nbs-bl.")
        pass 
    """
    #manipulator.load_sample_file(filename=file_path) ## Temporary testing to see what error gets thrown
    
    return

def save_sheet(file_path, file_label):
    ## Test comment + more comment
    save_configuration_spreadsheet_local(configuration=rsoxs_config["bar"], file_path=file_path, file_label=file_label)
    return








