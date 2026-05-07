##
import numpy as np
import copy
import datetime

from rsoxs.configuration_setup.configurations_instrument import load_configuration
from rsoxs.Functions.alignment import (
    #load_configuration, 
    load_samp, 
    rotate_now
    )
from rsoxs.HW.energy import set_polarization
from nbs_bl.plans.scans import nbs_count, nbs_list_scan, nbs_energy_scan
from rsoxs.plans.rsoxs import spiral_scan
from .default_energy_parameters import energy_list_parameters
from ..redis_config import rsoxs_config
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.hw import (
    en,
    mir1,
    fs6_cam,
    mirror2,
    grating,
    mir3,
    slitsc,
    slits1,
    izero_y,
    slits2,
    slits3,
    manipulator,
    sam_Th,
    #waxs_det,
    #Det_W,
)
from ..configuration_setup.configuration_load_save_sanitize import (
    gatherAcquisitionsFromConfiguration, 
    sanitizeAcquisition, 
    sortAcquisitionsQueue,
    updateConfigurationWithAcquisition,
)
from ..configuration_setup.configuration_load_save import sync_rsoxs_config_to_nbs_manipulator

import bluesky.plan_stubs as bps
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.samples import add_current_position_as_sample



def run_acquisitions_queue(
        configuration = copy.deepcopy(rsoxs_config.get("bar", {})),
        dryrun = True,
        sort_by = ["priority"], ## TODO: Not sure yet how to give it a list of groups in a particular order.  Maybe a list within a list.
        ):
    ## Run a series of single acquisitions

    ## For some reason, the configuration variable has to be set here.  If it is set in the input, it shows prior configuration, not the current one.
    ## TODO: Understand why 
    configuration = copy.deepcopy(rsoxs_config["bar"])

    acquisitions = gatherAcquisitionsFromConfiguration(configuration)
    ## TODO: Can only sort by "priority" at the moment, not by anything else
    queue = sortAcquisitionsQueue(acquisitions, sortBy=sort_by) 
    
    print("Starting queue")

    for indexAcquisition, acquisition in enumerate(queue):
        print("\n\n")
        yield from run_acquisitions_single(acquisition=acquisition, dryrun=dryrun)


    print("\n\nFinished queue")

    ## TODO: get time estimates for individual acquisitions and the full queue.  Import datetime and can print timestamps for when things actually completed.





## TODO: This function can benefit from refactoring.
## As is, a single iteration of this function does not necessarily correspond to a single scan.  It may run multiple scans with multiple corresponding scan IDs if, e.g., multiple angles and polarizations are given.
## As a result, the local uid and scan status are a bit misleading, as there might be multiple scans per spreadsheet line.
## One idea is to change the spreadsheet workflow so that multiple samples, energy lists, etc. can be entered onto a single spreadsheet line to avoid writing out every acquisition one-by-one.  And then a separate function can be used to generate a queue with with a single line corresponding to one acquisition.
## Separately, it would also be good to break this function into smaller sub-functions for better readability.

def run_acquisitions_single(
        acquisition,
        dryrun = True
):
    
    updateAcquireStatusDuringDryRun = False ## Hardcoded variable for troubleshooting.  False during normal operation, but True during troubleshooting.
    
    ## The acquisition is sanitized again in case it were not run from a spreadsheet
    ## But for now, still requires that a full configuration be set up for the sample
    acquisition = sanitizeAcquisition(acquisition) ## This would be run before if a spreadsheet were loaded, but now it will ensure the acquisition is sanitized in case the acquisition is run in the terminal
    
    parameter = "configuration_instrument"
    if acquisition[parameter] is not None:
        yield from load_configuration(
            configuration_name = acquisition[parameter],
            dryrun = dryrun,
            )  

    ## TODO: set up diodes to high or low gain
    ## But there are issues at the moment with setup_diode_i400() and most people don't use this, so leave it for now

    parameter = "sample_id"
    if acquisition[parameter] is not None:
        yield from load_samp(
            sample_id_or_index = acquisition[parameter], 
            dryrun = dryrun,
            ) 
        

    ## TODO: set temperature if needed, but this is lowest priority

    for indexAngle, sampleAngle in enumerate(acquisition["sample_angles"]):
        
        ## TODO: come up with better way to handle.
        ## This is mainly for cases where bar image and fiducials are not run.
        ## Rotation is either not needed or handled differently.
        if sampleAngle != "Do not rotate":
            ## TODO: Requires spots to be picked from image, so I have to comment when I don't have beam
            yield from rotate_now(
                theta = sampleAngle,
                dryrun = dryrun,
                ) ## TODO: What is the difference between rotate_sample and rotate_now?
        
        for indexPolarization, polarization in enumerate(acquisition["polarizations"]):
            print("Setting polarization: " + str(polarization))
            if dryrun == False: 
                ## If a timeScan or spiral is being run when I don't have beam (during shutdown or when another station is using beam), I don't want to make any changes to the energy or polarization.
                ## TODO: Actually, make this even smarter.  If RSoXS station does not have control or if cannot write EPU Epics PV, then do this
                if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
                else: yield from set_polarization(polarization)
            
            print("Running scan: " + str(acquisition["scan_type"]))
            if dryrun == False or updateAcquireStatusDuringDryRun == True:
                timeStamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                acquisition["acquire_status"] = "Started " + str(timeStamp)
                rsoxs_config["bar"] = updateConfigurationWithAcquisition(rsoxs_config["bar"], acquisition)
            if dryrun == False:
                if "time" in acquisition["scan_type"]:
                    if acquisition["scan_type"]=="time": use_2D_detector = False
                    if acquisition["scan_type"]=="time2D": use_2D_detector = True
                    energy = acquisition["energy_list_parameters"]
                    print("Setting energy: " + str(energy))
                    if dryrun == False: 
                        if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
                        else: yield from bps.mv(en, energy)
                    yield from nbs_count(num=acquisition["exposures_per_energy"], 
                                         use_2d_detector=use_2D_detector, 
                                         dwell=acquisition["exposure_time"],
                                         )
                
                if acquisition["scan_type"] == "spiral":
                    energy = acquisition["energy_list_parameters"]
                    print("Setting energy: " + str(energy))
                    if dryrun == False: 
                        if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
                        else: yield from bps.mv(en, energy)
                    ## TODO: could I just run waxs_spiral_mode() over here and then after spiral_scan finishes, run waxs_normal_mode()?  Eliot may have mentioned something about not being able to do this inside the Run Engine or within spreadsheet, but maybe get this clarified during data security?
                    yield from spiral_scan(
                        stepsize=acquisition["spiral_dimensions"][0], 
                        widthX=acquisition["spiral_dimensions"][1], 
                        widthY=acquisition["spiral_dimensions"][2],
                        n_exposures=acquisition["exposures_per_energy"], 
                        dwell=acquisition["exposure_time"],
                        )

                if acquisition["scan_type"] in ("nexafs", "rsoxs"):
                    print("Energy parameters: " + str(acquisition["energy_list_parameters"]))
                    if acquisition["scan_type"]=="nexafs": use_2D_detector = False
                    if acquisition["scan_type"]=="rsoxs": use_2D_detector = True
                    energy_parameters = acquisition["energy_list_parameters"]
                    if isinstance(energy_parameters, str): energy_parameters = energy_list_parameters[energy_parameters]
                    
                    ## If cycles = 0, then just run one sweep in ascending energy
                    if acquisition["cycles"] == 0: 
                        yield from nbs_energy_scan(
                                *energy_parameters,
                                use_2d_detector=use_2D_detector, 
                                dwell=acquisition["exposure_time"],
                                n_exposures=acquisition["exposures_per_energy"], 
                                group_name=acquisition["group_name"],
                                )
                    
                    ## If cycles is an integer > 0, then run pairs of sweeps going in ascending then descending order of energy
                    else: 
                        for cycle in np.arange(0, acquisition["cycles"], 1):
                            yield from nbs_energy_scan(
                                *energy_parameters,
                                use_2d_detector=use_2D_detector, 
                                dwell=acquisition["exposure_time"],
                                n_exposures=acquisition["exposures_per_energy"], 
                                group_name=acquisition["group_name"],
                                )
                            yield from nbs_energy_scan(
                                *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
                                use_2d_detector=use_2D_detector, 
                                dwell=acquisition["exposure_time"],
                                n_exposures=acquisition["exposures_per_energy"], 
                                group_name=acquisition["group_name"],
                                )
                    
                    ## TODO: maybe default to cycles = 1?  It would be good practice to have forward and reverse scan to assess reproducibility
            
            if dryrun == False or updateAcquireStatusDuringDryRun == True:
                timeStamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                acquisition["acquire_status"] = "Finished " + str(timeStamp) ## TODO: Add timestamp
                rsoxs_config["bar"] = updateConfigurationWithAcquisition(rsoxs_config["bar"], acquisition)

    sync_rsoxs_config_to_nbs_manipulator()






"""

for acq in myQueue:
    RE(runAcquisitions_Single(acquisition=acq, dryrun=True))




## Example queue dictionary


myQueue = [

{
"sampleID": "OpenBeam",
"configurationInstrument": "WAXSNEXAFS",
"scanType": "nexafs_step",
"energyListParameters": "carbon_NEXAFS",
"exposureTime": 1,
"exposuresPerEnergy": 1,
"sampleAngles": [0],
"polarizationFrame": "lab",
"polarizations": [0, 90],
"groupName": "IBM_NEXAFS",
"priority": 1,
},
{
"sampleID": "OpenBeam",
"configurationInstrument": "WAXSNEXAFS",
"scanType": "nexafs_step",
"energyListParameters": "oxygen_NEXAFS",
"exposureTime": 1,
"exposuresPerEnergy": 1,
"sampleAngles": [0],
"polarizationFrame": "lab",
"polarizations": [0, 90],
"groupName": "IBM_NEXAFS",
"priority": 1,
},
{
"sampleID": "OpenBeam",
"configurationInstrument": "WAXSNEXAFS",
"scanType": "nexafs_step",
"energyListParameters": "fluorine_NEXAFS",
"exposureTime": 1,
"exposuresPerEnergy": 1,
"sampleAngles": [0],
"polarizationFrame": "lab",
"polarizations": [0, 90],
"groupName": "IBM_NEXAFS",
"priority": 1,
},
{
"sampleID": "HOPG",
"configurationInstrument": "WAXSNEXAFS",
"scanType": "nexafs_step",
"energyListParameters": "carbon_NEXAFS",
"exposureTime": 1,
"exposuresPerEnergy": 1,
"sampleAngles": [20],
"polarizationFrame": "lab",
"polarizations": [90],
"groupName": "IBM_NEXAFS",
"priority": 1,
},

]



"""

