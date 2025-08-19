import bluesky.plans as bp
from operator import itemgetter
import copy
from copy import deepcopy
import collections
import numpy as np

from functools import partial
import bluesky.plan_stubs as bps
from ophyd import Device

from ..startup import RE, rsoxs_config  # bec, db
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
    Det_W,
    Beamstop_SAXS,
    BeamStopS,
    Det_S,
    #dm7,
)

from nbs_bl.samples import move_sample

## An alternative way to load devices is:
# from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
# Beamstop_SAXS = bl["Beamstop_SAXS"] ## what follows bl is the key in devices.toml in profile_collection contained in the []
from ..HW.signals import default_sigs
from ..HW.detectors import set_exposure  # , saxs_det
from ..HW.energy import en, set_polarization, grating_to_1200, grating_to_250, grating_to_rsoxs
from nbs_bl.printing import run_report, boxed_text, colored
from ..HW.slackbot import rsoxs_bot
from .common_functions import args_to_string

from .per_steps import take_exposure_corrected_reading, one_nd_sticky_exp_step

from .alignment_local import *


run_report(__file__)







def load_samp(
        sample_id_or_index, 
        ):
    """
    move to a sample location and load the metadata with the sample information from persistant sample list by index or sample_id

    """
    
    sample_id, sample_index = get_sample_id_and_index(sample_id_or_index=sample_id_or_index)
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



def rotate_now(theta, force=False):
    if theta is not None:
        
        ## Identify the current sample and get its metadata
        sample_id_current = RE.md["sample_id"] ## TODO: would like a better way to do this
        sample_id, sample_index = get_sample_id_and_index(sample_id_current)
        sample_dictionary_old = copy.deepcopy(rsoxs_config["bar"][sample_index])

        ## Set new angle, rotate to the angle, update rsoxs_config
        sample_dictionary_new = copy.deepcopy(sample_dictionary_old)
        sample_dictionary_new["angle"] = theta
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

"""
def sample():
    title = "Sample metadata - stored in every scan:"
    text = ""
    if len(str(RE.md["proposal_id"])) > 0:
        text += "   proposal ID:           " + colored("{}".format(RE.md["proposal_id"]).center(48, " "), "cyan")
    if len(str(RE.md["SAF"])) > 0:
        text += "\n   SAF id:                " + colored("{}".format(RE.md["SAF"]).center(48, " "), "cyan")
    if len(str(RE.md["institution"])) > 0:
        text += "\n   Institution:           " + colored("{}".format(RE.md["institution"]).center(48, " "), "cyan")
    if len(str(RE.md["sample_name"])) > 0:
        text += "\n   Sample Name:           " + colored("{}".format(RE.md["sample_name"]).center(48, " "), "cyan")
    if len(str(RE.md["sample_priority"])) > 0:
        text += "\n   Sample Priority:       " + colored(
            "{}".format(RE.md["sample_priority"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["sample_desc"])) > 0:
        text += "\n   Sample Description:    " + colored("{}".format(RE.md["sample_desc"]).center(48, " "), "cyan")
    if len(str(RE.md["sample_id"])) > 0:
        text += "\n   Sample ID:             " + colored(
            "{}".format(str(RE.md["sample_id"])).center(48, " "), "cyan"
        )
    if len(str(RE.md["sample_set"])) > 0:
        text += "\n   Sample Set:            " + colored("{}".format(RE.md["sample_set"]).center(48, " "), "cyan")
    if len(str(RE.md["sample_date"])) > 0:
        text += "\n   Sample Creation Date:  " + colored("{}".format(RE.md["sample_date"]).center(48, " "), "cyan")
    if len(str(RE.md["project_name"])) > 0:
        text += "\n   Project name:          " + colored(
            "{}".format(RE.md["project_name"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["project_desc"])) > 0:
        text += "\n   Project Description:   " + colored(
            "{}".format(RE.md["project_desc"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["bar_loc"]["spot"])) > 0:
        text += "\n   Location on Bar:       " + colored(
            "{}".format(RE.md["bar_loc"]["spot"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["bar_loc"]["th"])) > 0:
        text += "\n   Angle of incidence:    " + colored(
            "{}".format(RE.md["bar_loc"]["th"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["composition"])) > 0:
        text += "\n   Composition(formula):  " + colored("{}".format(RE.md["composition"]).center(48, " "), "cyan")
    if len(str(RE.md["density"])) > 0:
        text += "\n   Density:               " + colored(
            "{}".format(str(RE.md["density"])).center(48, " "), "cyan"
        )
    if len(str(RE.md["components"])) > 0:
        text += "\n   List of Components:    " + colored("{}".format(RE.md["components"]).center(48, " "), "cyan")
    if len(str(RE.md["thickness"])) > 0:
        text += "\n   Thickness:             " + colored(
            "{}".format(str(RE.md["thickness"])).center(48, " "), "cyan"
        )
    if len(str(RE.md["sample_state"])) > 0:
        text += "\n   Sample state:          " + colored(
            "{}".format(RE.md["sample_state"]).center(48, " "), "cyan"
        )
    if len(str(RE.md["notes"])) > 0:
        text += "\n   Notes:                 " + colored("{}".format(RE.md["notes"]).center(48, " "), "cyan")
    boxed_text(title, text, "red", 80, shrink=False)
"""

def get_location(motor_list):
    locs = []
    for motor in motor_list:
        locs.append({"motor": motor, "position": motor.user_readback.get(), "order": 0})
    return locs


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





def move_to_location(locs=get_sample_location()):
    for item in locs:
        item.setdefault("order", 0)
    locs = sorted(locs, key=itemgetter("order"))
    orderlist = [o for o in collections.Counter([d["order"] for d in locs]).keys()]

    switch = {
        "x": sam_X,
        "y": sam_Y,
        "z": sam_Z,
        "th": sam_Th,
        sam_X: sam_X,
        sam_Y: sam_Y,
        sam_Z: sam_Z,
        sam_Th: sam_Th,
        TEMZ: TEMZ,
        "TEMZ": TEMZ,
        slits1.vsize: slits1.vsize,
        slits1.hsize: slits1.hsize,
        slits2.vsize: slits2.vsize,
        slits2.hsize: slits2.hsize,
        slits3.vsize: slits3.vsize,
        slits3.hsize: slits3.hsize,
        slits1.vcenter: slits1.vcenter,
        slits1.hcenter: slits1.hcenter,
        slits2.vcenter: slits2.vcenter,
        slits2.hcenter: slits2.hcenter,
        slits3.vcenter: slits3.vcenter,
        slits3.hcenter: slits3.hcenter,
        shutter_y: shutter_y,
        izero_y: izero_y,
        Det_W: Det_W,
        Det_S: Det_S,
        BeamStopS: BeamStopS,
        BeamStopW: BeamStopW,
        slitsc: slitsc,
        #dm7: dm7,
    }
    for order in orderlist:

        """
        for items in locs:
            if items["order"] == order:
                if isinstance(items["position"], (list, redis_json_dict.redis_json_dict.ObservableSequence)): items["position"] = items["position"][0]
                outputlist = [
                            [switch[items["motor"]], float(items["position"])]
                        ]
        """
        ## 20241202 error while running load_samp: TypeError: float() argument must be a string or a real number, not 'ObservableSequence'

        outputlist = [
            [switch[items["motor"]], float(items["position"])] for items in locs if items["order"] == order
        ]

        flat_list = [item for sublist in outputlist for item in sublist]
        yield from bps.mv(*flat_list)






def get_sample_dict(acq=[], locations=None):
    if locations is None:
        locations = get_sample_location()
    sample_name = RE.md["sample_name"]
    sample_priority = RE.md["sample_priority"]
    #sample_desc = RE.md["sample_desc"]
    sample_id = RE.md["sample_id"]
    #sample_set = RE.md["sample_set"]
    #sample_date = RE.md["sample_date"]
    project_name = RE.md["project_name"]
    #proposal_id = RE.md["proposal_id"]
    #saf_id = RE.md["SAF"]
    institution = RE.md["institution"]
    project_desc = RE.md["project_desc"]
    composition = RE.md["composition"]
    bar_loc = RE.md["bar_loc"]
    #density = RE.md["density"]
    grazing = RE.md["grazing"]
    bar_spot = RE.md["bar_spot"]
    front = RE.md["front"]
    height = RE.md["height"]
    angle = RE.md["angle"]
    #components = RE.md["components"]
    #thickness = RE.md["thickness"]
    #sample_state = RE.md["sample_state"]
    notes = RE.md["notes"]

    return {
        "sample_name": sample_name,
        #"sample_desc": sample_desc,
        "sample_id": sample_id,
        "sample_priority": sample_priority,
        #"proposal_id": proposal_id,
        #"SAF": saf_id,
        "institution": institution,
        #"sample_set": sample_set,
        #"sample_date": sample_date,
        "project_name": project_name,
        "project_desc": project_desc,
        "composition": composition,
        "bar_loc": bar_loc,
        #"density": density,
        "grazing": grazing,
        "bar_spot": bar_spot,
        "front": front,
        "height": height,
        "angle": angle,
        #"components": components,
        #"thickness": thickness,
        #"sample_state": sample_state,
        "notes": notes,
        "location": locations,
        "acquisitions": acq,
    }


## Used to be used with load_samp
def load_sample(sam_dict, sim_mode=False):
    """
    move to a sample location and load the metadata with the sample information

    :param sam_dict: sample dictionary containing all metadata and sample location
    :return:
    """
    if sim_mode:
        return f"move to {sam_dict['sample_name']}"
    RE.md.update(sam_dict)
    yield from move_to_location(locs=sam_dict["location"])






def newsample():
    """
    ceate a new sample dictionary interactively

    :return: a sample dictionary
    """
    print(
        "This information will tag future data until this changes, please be as thorough as possible\n"
        "current values in parentheses, leave blank for no change"
    )
    sample_name = input("Your sample name  - be concise ({}): ".format(RE.md["sample_name"]))
    if sample_name != "":
        RE.md["sample_name"] = sample_name

    sample_priority = input(
        "Your sample priority  - 0 - highest to 100-lowest ({}): ".format(RE.md["sample_priority"])
    )
    if sample_priority != "":
        RE.md["sample_priority"] = sample_priority

    sample_desc = input("Describe your sample - be thorough ({}): ".format(RE.md["sample_desc"]))
    if sample_desc != "":
        RE.md["sample_desc"] = sample_desc

    sample_id = input("Your sample id - if you have one ({}): ".format(RE.md["sample_id"]))
    if sample_id != "":
        RE.md["sample_id"] = sample_id

    proposal_id = input("Your Proposal ID from PASS ({}): ".format(RE.md["proposal_id"]))
    if proposal_id != "":
        RE.md["proposal_id"] = proposal_id

    institution = input("Your Institution ({}): ".format(RE.md["institution"]))
    if institution != "":
        RE.md["institution"] = institution

    saf_id = input("Your SAF ID number from PASS ({}): ".format(RE.md["SAF"]))
    if saf_id != "":
        RE.md["SAF"] = saf_id

    sample_set = input("What set does this sample belong to ({}): ".format(RE.md["sample_set"]))
    if sample_set != "":
        RE.md["sample_set"] = sample_set

    sample_date = input("Sample creation date ({}): ".format(RE.md["sample_date"]))
    if sample_date != "":
        RE.md["sample_date"] = sample_date

    project_name = input("Is there an associated project name ({}): ".format(RE.md["project_name"]))
    if project_name != "":
        RE.md["project_name"] = project_name

    project_desc = input("Describe the project ({}): ".format(RE.md["project_desc"]))
    if project_desc != "":
        RE.md["project_desc"] = project_desc

    bar_loc = input("Location on the Bar ({}): ".format(RE.md["bar_loc"]["spot"]))
    if bar_loc != "":
        RE.md["bar_loc"]["spot"] = bar_loc
        RE.md["bar_spot"] = bar_loc

    th = input(
        "Angle desired for sample acquisition (-180 for transmission from back) ({}): ".format(
            RE.md["bar_loc"]["th"]
        )
    )
    if th != "":
        RE.md["bar_loc"]["th"] = float(th)
        RE.md["angle"] = float(th)

    composition = input("Sample composition or chemical formula ({}): ".format(RE.md["composition"]))
    if composition != "":
        RE.md["composition"] = composition

    density = input("Sample density ({}): ".format(RE.md["density"]))
    if density != "":
        RE.md["density"] = density

    components = input("Sample components ({}): ".format(RE.md["components"]))
    if components != "":
        RE.md["components"] = components

    thickness = input("Sample thickness ({}): ".format(RE.md["thickness"]))
    if thickness != "":
        RE.md["thickness"] = thickness

    sample_state = input('Sample state "Broken/Fresh" ({}): '.format(RE.md["sample_state"]))
    if sample_state != "":
        RE.md["sample_state"] = sample_state

    notes = input("Sample notes ({}): ".format(RE.md["notes"]))
    if notes != "":
        RE.md["notes"] = notes

    grazing = input("Is the sample for grazing incidence? ({}): ".format(RE.md["grazing"]))
    if grazing != "":
        RE.md["grazing"] = bool(grazing)
    front = input("Is the sample on the front of the bar? ({}): ".format(RE.md["front"]))
    if front != "":
        RE.md["front"] = bool(front)
    height = input("Sample height? ({}): ".format(RE.md["height"]))
    if height != "":
        RE.md["height"] = float(height)

    RE.md["acquisitions"] = []

    loc = input(
        "New Location? (if blank use current location x={:.2f},y={:.2f},z={:.2f},th={:.2f}): ".format(
            sam_X.user_readback.get(),
            sam_Y.user_readback.get(),
            sam_Z.user_readback.get(),
            sam_Th.user_readback.get(),
        )
    )
    if loc != "":
        locs = []
        xval = input("X ({:.2f}): ".format(sam_X.user_readback.get()))
        if xval != "":
            locs.append({"motor": "x", "position": xval, "order": 0})
        else:
            locs.append({"motor": "x", "position": sam_X.user_readback.get(), "order": 0})
        yval = input("Y ({:.2f}): ".format(sam_Y.user_readback.get()))
        if yval != "":
            locs.append({"motor": "y", "position": yval, "order": 0})
        else:
            locs.append({"motor": "y", "position": sam_Y.user_readback.get(), "order": 0})

        zval = input("Z ({:.2f}): ".format(sam_Z.user_readback.get()))
        if zval != "":
            locs.append({"motor": "z", "position": zval, "order": 0})
        else:
            locs.append({"motor": "z", "position": sam_Z.user_readback.get(), "order": 0})

        thval = input("Theta ({:.2f}): ".format(sam_Th.user_readback.get()))
        if thval != "":
            locs.append({"motor": "th", "position": thval, "order": 0})
        else:
            locs.append({"motor": "th", "position": sam_Th.user_readback.get(), "order": 0})
        return get_sample_dict(locations=locs, acq=[])
    else:
        return get_sample_dict(acq=[])  # uses current location by default


def alignment_rel_scan(det, motor, start_rel, end_rel, steps):
    savemd = RE.md.deepcopy()


# Spiral searches


def samxscan():
    yield from psh10.open()
    yield from bp.rel_scan([Beamstop_SAXS], sam_X, -2, 2, 41)
    yield from psh10.close()







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
