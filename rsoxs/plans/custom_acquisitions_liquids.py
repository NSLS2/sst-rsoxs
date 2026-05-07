import numpy as np
import copy

import bluesky.plan_stubs as bps

from nbs_bl.hw import (
    en,
    slits1,
    gvll,
    gv_tem,
    TEMY,
    TEMZ,
)
from nbs_bl.plans.scans import nbs_count
from ..redis_config import rsoxs_config
from ..Functions.alignment import (
    get_sample_id_and_index, 
    duplicate_sample, 
    load_samp,
)
from ..configuration_setup.configuration_load_save import sync_rsoxs_config_to_nbs_manipulator
from ..configuration_setup.configurations_instrument import load_configuration
from .run_acquisitions import run_acquisitions_single


def solids_to_TEM():
    """
    """

    solids_in_beam = True
    while solids_in_beam:
        yield from load_configuration("SolidSamples_Retracted")
        print("Have you closed the solid samples load lock gate valve? (y/n)")
        solids_gate_valve_closed_1 = input()
        solids_gate_valve_closed_2 = gvll.read()["Load Lock Gate Valve_cls"]["value"]

        if (
            solids_gate_valve_closed_1 == "y"
            and solids_gate_valve_closed_2 == 1 
        ):
            solids_in_beam = False
        else:
            print("Please check that solid samples have been retracted and that the load lock is closed.")

    TEM_load_lock_closed = True
    while TEM_load_lock_closed:
        print("Have you opened the TEM load lock gate valve? (y/n)")
        TEM_load_lock_opened_1 = input()
        TEM_load_lock_opened_2 = gv_tem.read()["TEM Load Lock Gate Valve_opn"]["value"]

        if (
            TEM_load_lock_opened_1 == "y"
            and TEM_load_lock_opened_2 == 1
        ):
            TEM_load_lock_closed = False
        else:
            print("Please check that TEM load lock is open.")
    
    ## Move TEM sample into beam path
    yield from load_configuration("TEMSample")

    print("TEM sample has been safely moved into the beam path.  You may proceed with measurements.")


def TEM_to_solids():
    """
    """

    TEM_in_beam = True
    while TEM_in_beam:
        yield from load_configuration("TEMSample_Retracted")
        print("Have you closed the TEM load lock gate valve? (y/n)")
        TEM_load_lock_closed_1 = input()
        TEM_load_lock_closed_2 =  gv_tem.read()["TEM Load Lock Gate Valve_cls"]["value"]

        if (
            TEM_load_lock_closed_1 == "y"
            and TEM_load_lock_closed_2 == 1
        ):
            TEM_in_beam = False
        else:
            print("Please check that the TEM sample has been retracted and that the load lock is closed.")

    solids_load_lock_closed = True
    while solids_load_lock_closed:
        print("Have you opened the solids load lock gate valve? (y/n)")
        solids_load_lock_opened_1 = input()
        solids_load_lock_opened_2 = gvll.read()["Load Lock Gate Valve_opn"]["value"]

        if (
            solids_load_lock_opened_1 == "y"
            and solids_load_lock_opened_2 == 1
        ):
            solids_load_lock_closed = False
        else:
            print("Please check that solids load lock is open.")

    ## No need to explicitly move solids into beam path.  Acquisition queue will do that automatically.

    print("TEM sample has been safely moved out the beam path.  You may proceed with solids measurements.")



def create_sample(
        sample_metadata = {
            "sample_id": None,
            "project_name": None,
            "institution": None,
            "proposal_id": None,
            "notes": None,
        },
        sample_id_to_duplicate = "TEM",
):
    """
    """

    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])







def TEM_acquisitions(
        queue = None,
        dryrun = True,
):
    """
    Alternative to running queue in spreadsheet
    """

    ## Define sample metadata
    sample_metadata = {
            "sample_id": "Water-2_20260302",
            "project_name": "LiquidSolventsLibrary",
            "institution": "NIST",
            "proposal_id": 318915,
            "notes": "SRS570 sensitivity 5 nA/V",
        }
    sample_id_to_duplicate = "TEM"

    ## Set up queue as a pre-loaded script below or create it in iPython
    if queue is None:
        template_acquisition = {
        "sample_id": sample_metadata["sample_id"],
        "configuration_instrument": "DM7NEXAFS_Liquids",
        "scan_type": "nexafs",
        "energy_list_parameters": "carbon_NEXAFS",
        "polarizations": [0], 
        "exposure_time": 1,
        "cycles": 1,
        "sample_angles": "Do not rotate",
        "group_name": "Liquids NEXAFS",
        "priority": 1,
        "notes": "SRS570 sensitivity 5 nA/V, 200 mbar",
        }

        queue = [template_acquisition]

        for energy_parameters in ["oxygen_NEXAFS"]:
            acquisition = copy.deepcopy(template_acquisition)
            acquisition["energy_list_parameters"] = energy_parameters
            acquisition["priority"] = queue[-1]["priority"] + 1
            queue.append(acquisition)



    ## Automated steps t ocreate sample
    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])


    ## Run queue
    for iteration in np.arange(1, 100, 1):
        for acq in queue:
            yield from run_acquisitions_single(
                acquisition = acq, 
                dryrun = dryrun
                )
            print("\n\n")





def TEM_acquisitions_cell_position_offset(
        queue = None,
        dryrun = True,
):
    """
    Alternative to running queue in spreadsheet
    """

    ## Define sample metadata
    sample_metadata = {
            "sample_id": "EmptyCell_20260211",
            "project_name": "LiquidSolventsLibrary",
            "institution": "NIST",
            "proposal_id": 318915,
            "notes": "SRS570 sensitivity 5 nA/V, N2 flowing through window",
        }
    sample_id_to_duplicate = "TEM"

    ## Set up queue as a pre-loaded script below or create it in iPython
    if queue is None:
        template_acquisition = {
        "sample_id": sample_metadata["sample_id"],
        "configuration_instrument": "DM7NEXAFS_Liquids",
        "scan_type": "nexafs",
        "energy_list_parameters": "carbon_NEXAFS",
        "polarizations": [0], 
        "exposure_time": 1,
        "cycles": 0,
        "sample_angles": "Do not rotate",
        "group_name": "Liquids NEXAFS",
        "priority": 1,
        "notes": "SRS570 sensitivity 5 nA/V, N2 flowing through window",
        }

        queue = [template_acquisition]

        for energy_parameters in []:
            acquisition = copy.deepcopy(template_acquisition)
            acquisition["energy_list_parameters"] = energy_parameters
            acquisition["priority"] = queue[-1]["priority"] + 1
            queue.append(acquisition)



    ## Automated steps t ocreate sample
    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])


    ## Run queue
    for iteration in np.arange(0, 5, 1):
        print("Moving TEM inboard-outboard to 1.")
        yield from bps.mv(TEMZ, 1)
        print("Moving TEM inboard-outboard to 139.7.")
        yield from bps.mv(TEMZ, 139.7)

        for acq in queue:
            yield from run_acquisitions_single(
                    acquisition = acq, 
                    dryrun = dryrun,
                    )
            
            print("\n\n")
    
    yield from bps.mv(en, 270)
    yield from nbs_count(
                        num=300, 
                        dwell=1,
                        )



















## Amanda
def TEM_sodium(
        queue = None,
        dryrun = True,
):
    """
    Alternative to running queue in spreadsheet
    """

    ## Define sample metadata
    sample_metadata = {
            "sample_id": "1MNa",
            "project_name": "Carr",
            "institution": "ANL",
            "proposal_id": 317132,
            "notes": None,
        }
    sample_id_to_duplicate = "TEM"

    ## Set up queue as a pre-loaded script below or create it in iPython
    if queue is None:
        template_acquisition = {
        "sample_id": sample_metadata["sample_id"],
        "configuration_instrument": "DM7NEXAFS_Liquids",
        "scan_type": "nexafs",
        "energy_list_parameters": "sodium_NEXAFS",
        "polarizations": [0], 
        "exposure_time": 1,
        "cycles": 1,
        "sample_angles": "Do not rotate",
        "group_name": "Liquids NEXAFS",
        "priority": 1,
        "notes": "",
        }

        queue = [template_acquisition]

    ## Automated steps t ocreate sample
    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])


    ## Run queue
    for acq in queue:
        yield from run_acquisitions_single(
            acquisition = acq, 
            dryrun = dryrun,
                )
        print("\n\n")

def TEM_calcium(
        queue = None,
        dryrun = True,
):
    """
    Alternative to running queue in spreadsheet
    """

    ## Define sample metadata
    sample_metadata = {
            "sample_id": "1MCa",
            "project_name": "Carr",
            "institution": "ANL",
            "proposal_id": 317132,
            "notes": None,
        }
    sample_id_to_duplicate = "TEM"

    ## Set up queue as a pre-loaded script below or create it in iPython
    if queue is None:
        template_acquisition = {
        "sample_id": sample_metadata["sample_id"],
        "configuration_instrument": "DM7NEXAFS_Liquids",
        "scan_type": "nexafs",
        "energy_list_parameters": "calciumLscan_NEXAFS",
        "polarizations": [0], 
        "exposure_time": 1,
        "cycles": 1,
        "sample_angles": "Do not rotate",
        "group_name": "Liquids NEXAFS",
        "priority": 1,
        "notes": "",
        }

        queue = [template_acquisition]

    ## Automated steps t ocreate sample
    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])


    ## Run queue
    for acq in queue:
        yield from run_acquisitions_single(
            acquisition = acq, 
            dryrun = dryrun,
                )
        print("\n\n")


