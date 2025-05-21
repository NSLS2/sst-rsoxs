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

from ..plans.default_energy_parameters import energyListParameters

from .configuration_load_save_sanitize import load_configuration_spreadsheet_local, save_configuration_spreadsheet_local
from ..redis_config import rsoxs_config


def load_sheet(file_path):
    configuration = load_configuration_spreadsheet_local(file_path=file_path)
    rsoxs_config["bar"] = copy.deepcopy(configuration)
    print("Replaced persistent configuration with configuration loaded from file path: " + str(file_path))
    return

def save_sheet(file_path, file_label):
    ## Test comment
    save_configuration_spreadsheet_local(configuration=rsoxs_config["bar"], file_path=file_path, file_label=file_label)
    return








