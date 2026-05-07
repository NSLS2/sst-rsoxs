import bluesky.plans as bp
from operator import itemgetter
import copy
from copy import deepcopy
import collections
import numpy as np

from functools import partial
import bluesky.plan_stubs as bps
from ophyd import Device

from ..redis_config import rsoxs_config  # bec, db
from ..configuration_setup.configuration_load_save import sync_rsoxs_config_to_nbs_manipulator

from nbs_bl.hw import (
    psh10,
    slitsc,
    slits1,
    izero_y,
    shutter_control,
    shutter_y,
    slits2,
    slits3,
    manipulator,
    sam_X,
    sam_Y,
    sam_Th,
    sam_Z,
    TEMX,
    TEMY,
    TEMZ,
    BeamStopW,
    #Det_W,
    #Beamstop_SAXS,
    #BeamStopS,
    #Det_S,
    #dm7,
)

from nbs_bl.samples import move_sample

## An alternative way to load devices is:
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
# Beamstop_SAXS = bl["Beamstop_SAXS"] ## what follows bl is the key in devices.toml in profile_collection contained in the []
from ..HW.signals import default_sigs
from ..HW.detectors import set_exposure  # , saxs_det
from nbs_bl.printing import run_report, boxed_text, colored
from ..HW.slackbot import rsoxs_bot




from .alignment_local import *

run_report(__file__)

RE = bl.run_engine

def load_samp(
        sample_id_or_index, 
        dryrun = False,
        ):
    """
    move to a sample location and load the metadata with the sample information from persistant sample list by index or sample_id

    """
    
    sample_id, sample_index = get_sample_id_and_index(sample_id_or_index=sample_id_or_index)

    print("Loading sample: " + str(sample_id))

    if dryrun == True: return

    yield from move_sample(sample_id)
    RE.md.update(rsoxs_config["bar"][sample_index])


def get_sample_id_and_index(sample_id_or_index):
    """
    Returns both sample_id and index number (from sample list) from an input that is either the sample_id or index.

    See sst-rsoxs issue #37 https://github.com/NSLS2/sst-rsoxs/issues/37 for motivation.
    """
    
    if isinstance(sample_id_or_index, int): ## Sample index was inputted
        try: 
            sample_id = rsoxs_config["bar"][sample_id_or_index]["sample_id"]
            sample_index = sample_id_or_index
        except: raise ValueError("Sample number" + str(sample_id_or_index) + "not found.")
    elif isinstance(sample_id_or_index, str): ## Sample name was inputted
        sample_found = False
        for index, sample in enumerate(rsoxs_config["bar"]):
            if sample["sample_id"] == sample_id_or_index:
                sample_index = index
                sample_id = sample_id_or_index
                sample_found = True
                break
        if sample_found == False: raise ValueError("Sample ID" + str(sample_id_or_index) + "not found.")
    
    return sample_id, int(sample_index)


def duplicate_sample(sample_index, name_suffix):
    """
    Creates a new sample by adding a new suffix followed by underscore on the old sample name.
    Useful for picking multiple spots on the same sample.
    """

    ## TODO: have function take in both sample_id and index?

    new_sample_dictionary = copy.deepcopy(rsoxs_config['bar'][sample_index])
    
    ## Set the current location and update sample name/id
    new_sample_dictionary["location"] = get_sample_location()
    new_sample_dictionary["sample_name"] += f"_{name_suffix}"
    new_sample_dictionary["sample_id"] += f"_{name_suffix}"

    ## Clear acquisitions so that there is no unwanted new acquisitions added to the list.
    new_sample_dictionary["acquisitions"] = []

    rsoxs_config["bar"].append(new_sample_dictionary)
    sync_rsoxs_config_to_nbs_manipulator()



def rotate_now(
        theta, 
        force = False,
        dryrun = False,
):
    if theta is not None:
        
        ## Identify the current sample and get its metadata
        sample_id_current = RE.md["sample_id"] ## TODO: would like a better way to do this
        sample_id, sample_index = get_sample_id_and_index(sample_id_current)
        sample_dictionary_old = copy.deepcopy(rsoxs_config["bar"][sample_index])
        ## Set new angle
        sample_dictionary_new = copy.deepcopy(sample_dictionary_old)
        sample_dictionary_new["angle"] = theta

        print("Rotating to angle: " + str(theta))
        if dryrun == True: return
        ## Rotate to angle, update rsoxs_config
        rotate_sample(sample_dictionary_new, force)
        rsoxs_config["bar"][sample_index] = sample_dictionary_new
        sync_rsoxs_config_to_nbs_manipulator()

        ## Load the sample with new metadata
        yield from load_samp(sample_index)

        ## TODO: Come up with a better way to set the angle in the metadata.
        ## As is, it will persistently store the new angle we rotated to when ideally I would like to restore the old sample dictionary.
        ## For spreadsheet runs, it's fine because sample angle defaults to 0 or is explicitly defined.
        ## But for manual rotations, we will have to rotate back explicitly.
        ## TODO: Change spreadsheet workflow so that angle is only defined in acquisitions, not samples tab.  Have all angles default to normal incidence, as that is how I align the bar anyways.











## Eliot's code


## TODO: Unsure if this function is actually used or needed.  Check and delete.
def sample_set_location(num):
    sample_dict = rsoxs_config["bar"][num]
    sample_dict["location"] = get_sample_location()  # set the location metadata
    # sample_recenter_sample(
    #     sample_dict
    # )  # change the x0, y0, theta to result in this new position (including angle)
    # return sample_dict
    sync_rsoxs_config_to_nbs_manipulator()


def get_sample_location():
    locs = []
    locs.append({"motor": "x", "position": sam_X.user_readback.get(), "order": 0})
    locs.append({"motor": "y", "position": sam_Y.user_readback.get(), "order": 0})
    locs.append({"motor": "z", "position": sam_Z.user_readback.get(), "order": 0})
    locs.append({"motor": "th", "position": sam_Th.user_readback.get(), "order": 0})
    #  locs = get_location([sam_X,sam_Y,sam_Z,sam_Th])
    return locs






def jog_samp_zoff(id_or_num, jog_val, write_default=True, move=True):
    # jogs the zoffset of a sample by some mm and optionally moves to the new position
    samp = samp_dict_from_id_or_num(id_or_num)
    if jog_val < -5 or jog_val > 5:
        raise ValueError("invalid jog value with magnitude > 5 was entered, start with something small")
    if "bar_loc" in samp:
        if "zoff" in samp["bar_loc"]:
            samp["bar_loc"]["zoff"] += jog_val
            if write_default:
                rotate_sample(
                    samp
                )  # this will write the new rotated positions into the position (without moving anything)
            if move:
                RE(load_samp(id_or_num))
        else:
            raise ValueError(
                f'the sample {samp["sample_name"]} does not appear to have a zoff yet, have you corrected positions?'
            )
    else:
        raise ValueError(
            f'the sample {samp["sample_name"]} does not appear to have a bar_loc field yet, have you imaged the sample positions?'
        )
    
    sync_rsoxs_config_to_nbs_manipulator()
