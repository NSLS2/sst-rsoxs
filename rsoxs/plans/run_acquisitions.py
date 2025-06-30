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
from nbs_bl.plans.scans import nbs_count, nbs_energy_scan
from rsoxs.plans.rsoxs import spiral_scan
from .default_energy_parameters import energyListParameters
from rsoxs.HW.detectors import snapshot
from ..startup import rsoxs_config
from nbs_bl.hw import (
    en,
)
from ..configuration_setup.configuration_load_save_sanitize import (
    gatherAcquisitionsFromConfiguration, 
    sanitizeAcquisition, 
    sortAcquisitionsQueue,
    updateConfigurationWithAcquisition,
)
from ..configuration_setup.configuration_load_save import sync_rsoxs_config_to_nbs_manipulator

import bluesky.plan_stubs as bps
from nbs_bl.samples import add_current_position_as_sample



def run_acquisitions_queue(
        configuration = copy.deepcopy(rsoxs_config["bar"]),
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
        yield from run_acquisitions_single(acquisition=acquisition, dryrun=dryrun)

    print("\n\nFinished queue")

    ## TODO: get time estimates for individual acquisitions and the full queue.  Import datetime and can print timestamps for when things actually completed.



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
        print("\n\n Loading instrument configuration: " + str(acquisition[parameter]))
        if dryrun == False: yield from load_configuration(acquisition[parameter])  

    ## TODO: set up diodes to high or low gain
    ## But there are issues at the moment with setup_diode_i400() and most people don't use this, so leave it for now

    parameter = "sample_id"
    if acquisition[parameter] is not None:
        print("Loading sample: " + str(acquisition[parameter]))
        if dryrun == False: 
            ## Don't move motors if I don't have beam.
            if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
            else: yield from load_samp(acquisition[parameter]) ## TODO: what is the difference between load_sample (loads from dict) and load_samp(loads from id or number)?  Can they be consolidated?
        

    ## TODO: set temperature if needed, but this is lowest priority

    for indexAngle, sampleAngle in enumerate(acquisition["sample_angles"]):
        print("Rotating to angle: " + str(sampleAngle))
        ## TODO: Requires spots to be picked from image, so I have to comment when I don't have beam
        if dryrun == False: 
            if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
            else: yield from rotate_now(sampleAngle) ## TODO: What is the difference between rotate_sample and rotate_now?
        
        for indexPolarization, polarization in enumerate(acquisition["polarizations"]):
            print("Setting polarization: " + str(polarization))
            if dryrun == False: 
                ## If a timeScan or spiral is being run when I don't have beam (during shutdown or when another station is using beam), I don't want to make any changes to the energy or polarization.
                ## TODO: Actually, make this even smarter.  If RSoXS station does not have control or if cannot write EPU Epics PV, then do this
                if acquisition["configuration_instrument"] == "NoBeam": print("Not moving motors.")
                else: yield from set_polarization(polarization)
            
            print("Running scan: " + str(acquisition["scan_type"]))
            add_current_position_as_sample(name=acquisition[parameter], sample_id=acquisition[parameter]) ## Probably temporary until we figure have this as part of load_samp.  Adding here so all angle rotations are included.
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
                                         sample=acquisition["sample_id"],
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
                        sample=acquisition["sample_id"],
                        )

                if acquisition["scan_type"] in ("nexafs", "rsoxs"):
                    if acquisition["scan_type"]=="nexafs": use_2D_detector = False
                    if acquisition["scan_type"]=="rsoxs": use_2D_detector = True
                    energyParameters = acquisition["energy_list_parameters"]
                    if isinstance(energyParameters, str): energyParameters = energyListParameters[energyParameters]
                    #yield from snapshot(secs=acquisition["exposure_time"])
                    yield from nbs_energy_scan(
                            *energyParameters,
                            use_2d_detector=use_2D_detector, 
                            dwell=acquisition["exposure_time"],
                            n_exposures=acquisition["exposures_per_energy"], 
                            group_name=acquisition["group_name"],
                            sample=acquisition["sample_id"],
                            )
            
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
