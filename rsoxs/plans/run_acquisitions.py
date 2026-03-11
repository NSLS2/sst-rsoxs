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
from ..Functions.energyscancore import cdsaxs_scan
from ..Functions.rsoxs_plans import do_rsoxs
from rsoxs.plans.rsoxs import spiral_scan
from .default_energy_parameters import energy_list_parameters
from rsoxs.HW.detectors import snapshot
from ..startup import rsoxs_config
from nbs_bl.hw import (
    en,
    mir1,
    fs6_cam,
    mirror2,
    grating,
    slitsc,
    slits1,
    izero_y,
    slits2,
    slits3,
    manipulator,
    sam_Th,
    waxs_det,
    Det_W,
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
        print("\n\n Loading instrument configuration: " + str(acquisition[parameter]))
        if dryrun == False: yield from load_configuration(acquisition[parameter])  

    ## TODO: set up diodes to high or low gain
    ## But there are issues at the moment with setup_diode_i400() and most people don't use this, so leave it for now

    parameter = "sample_id"
    if acquisition[parameter] is not None:
        print("Loading sample: " + str(acquisition[parameter]))
        if dryrun == False: 
            yield from load_samp(acquisition[parameter]) ## TODO: what is the difference between load_sample (loads from dict) and load_samp(loads from id or number)?  Can they be consolidated?
        

    ## TODO: set temperature if needed, but this is lowest priority

    for indexAngle, sampleAngle in enumerate(acquisition["sample_angles"]):
        print("Rotating to angle: " + str(sampleAngle))
        ## TODO: Requires spots to be picked from image, so I have to comment when I don't have beam
        if dryrun == False: 
            yield from rotate_now(sampleAngle) ## TODO: What is the difference between rotate_sample and rotate_now?
        
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


## Custom scripts for commissioning #################################




def commissioning_scans_20251201():

    
    yield from spirals_WSU()

    yield from HOPG_energy_resolution_series()

    yield from open_beam_waxs_photodiode_scans(iterations=1)

    yield from count_beam_stability()

    yield from zero_order_scans()

    yield from WAXS_camera_position_offset_scans()

    yield from open_beam_waxs_photodiode_scans(iterations=1000)
        
    


def spirals_WSU():

    print("Starting WSU spirals")


    sample_ids = [
        #"PC0",
        #"PC2",
        #"PC4",
        #"BD1-1",
        #"BD2-1",
        #"BD3-1",
        #"blank",
        "50nmPS",
    ]

    yield from set_polarization(0)
    yield from bps.mv(en, 270)

    yield from load_configuration("WAXS")

    for sample_id in sample_ids:
        print("Loading sample: " + str(sample_id))
        yield from load_samp(sample_id)

        yield from spiral_scan(
                        stepsize=0.3, 
                        widthX=1.8, 
                        widthY=1.8,
                        n_exposures=1, 
                        dwell=0.1,
                        )



def count_beam_stability():
    
    print("Starting counting scans")
    
    energies = np.arange(250, 350, 10)
    exposure_times = np.arange(1, 6, 1)

    yield from set_polarization(0)
    yield from load_configuration("WAXSNEXAFS")
    yield from load_samp("OpenBeam")

    for exposure_time in exposure_times:
        print("Exposure time: " + str(exposure_time))
        for energy in energies:
            print("Energy: " + str(energy))
            yield from bps.mv(en, energy)

            yield from nbs_count(
                num=100, 
                use_2d_detector=False, 
                dwell=exposure_time,
                                            )









        

    





def reproduce_EPU_error():

    add_current_position_as_sample(name="EPUTest", sample_id="EPUTest")

    for iteration in np.arange(0, 1e10, 1):
        for polarization in [0, 90, 45, 135]:
            yield from set_polarization(polarization)

            ## Running 50 repeat exposures at each energy at 1 s exposure time each.
            energy_parameters = (440, 120, 560)
            yield from nbs_energy_scan(
                                *energy_parameters,
                                use_2d_detector=False, 
                                dwell=1,
                                n_exposures=1,  
                                group_name="",
                                sample="EPUTest",
            )


## 20250711 mirror alignment parameter sweep to loop overnight
def M1_parameter_sweep_FS6():   
    comment_front_end = "FS6 image.  Front-end slits all the way open to hsize=7, hcenter=0.52, vsize=5, vcenter=-0.6.  FOE slits opened all the way to outboard=5, inboard=-5, top=5, bottom=-5."
    
    """
    ## Not going to change y and z
    comment_M1_y_z = comment_front_end + "  Mirror 1 y=-18, z=0"
    comment_M1_x_pitch = comment_M1_y_z
    
    ## First let's keep M1 x and pitch the same and just sweep the others
    M1_x = 1.3
    yield from bps.mv(mir1.x, M1_x)
    comment_M1_x_pitch = comment_M1_x_pitch + ", x=" + str(M1_x)
    M1_pitch = 0.57
    yield from bps.mv(mir1.pitch, M1_pitch)
    comment_M1_x_pitch = comment_M1_x_pitch + ", pitch=" + str(M1_pitch)


    for M1_yaw in np.arange(-10, 10, 1):
        yield from bps.mv(mir1.yaw, M1_yaw)
        comment = comment_M1_x_pitch + ", yaw=" + str(M1_yaw)

        for M1_roll in np.arange(-10, 10, 1):
            yield from bps.mv(mir1.roll, M1_roll)
            comment = comment + ", roll=" + str(M1_roll)

            yield from nbs_count(extra_dets=[fs6_cam], num=1, comment=comment)
    
    """

    
    ## Start at the defaults and do 1D sweeps
    ## TODO: load mirror configuration and run that way
    yield from bps.mv(mir1.x, 1.3)
    yield from bps.mv(mir1.y, -18)
    yield from bps.mv(mir1.z, 0)
    yield from bps.mv(mir1.pitch, 0.57)
    yield from bps.mv(mir1.yaw, 0)
    yield from bps.mv(mir1.roll, 0)

    for M1_roll in np.arange(-10, 10, 1):
        yield from bps.mv(mir1.roll, M1_roll)
        comment = comment_front_end + "  Mirror 1 x=1.3, y=-18, z=0, pitch=0.57, yaw=0"
        comment = comment + ", roll=" + str(M1_roll)
        
        yield from nbs_count(extra_dets=[fs6_cam], num=1, comment=comment)

    yield from bps.mv(mir1.roll, 0)
    for M1_yaw in np.arange(-10, 10, 1):
        yield from bps.mv(mir1.yaw, M1_yaw)
        comment = comment_front_end + "  Mirror 1 x=1.3, y=-18, z=0, pitch=0.57"
        comment = comment + ", yaw=" + str(M1_yaw)
        comment = comment + ", roll=0"
        
        yield from nbs_count(extra_dets=[fs6_cam], num=1, comment=comment)

    yield from bps.mv(mir1.yaw, 0)
    for M1_x in np.array([-3, -2, -1, -0.9, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1,4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 3]):
        yield from bps.mv(mir1.x, M1_x)
        comment = comment_front_end + "  Mirror 1 x=" + str(M1_x)
        comment = comment + ", y=-18, z=0, pitch=0.57, yaw=0, roll=0"
        
        yield from nbs_count(extra_dets=[fs6_cam], num=1, comment=comment)
    
    yield from bps.mv(mir1.x, 1.3)
    for M1_pitch in np.arange(0, 2.5, 0.01):
        yield from bps.mv(mir1.pitch, M1_pitch)
        comment = comment_front_end + "  Mirror 1 x=1.3, y=-18, z=0"
        comment = comment + ", pitch=" + str(M1_pitch)
        comment = comment + ", yaw=0, roll=0"
        
        yield from nbs_count(extra_dets=[fs6_cam], num=1, comment=comment)

    

    ## Return back to defaults
    yield from bps.mv(mir1.x, 1.3)
    yield from bps.mv(mir1.y, -18)
    yield from bps.mv(mir1.z, 0)
    yield from bps.mv(mir1.pitch, 0.57)
    yield from bps.mv(mir1.yaw, 0)
    yield from bps.mv(mir1.roll, 0)


    ## Didn't run this at this point but would be good to have a movie
    ## TODO: In the future, sweeps of how the beam looks at different EPU gaps and phases would be good as well
    comment = comment_front_end + "  Mirror 1 x=1.3, y=-18, z=0, pitch=0.57, yaw=0, roll=0"
    yield from nbs_count(extra_dets=[fs6_cam], num=10000000000, comment=comment)



    


def I0_mesh_vertical_profile_energy_scan():


    
    ## Full scan set
    I0_positions = np.arange(-42.8, -24, 0.2) ## TODO: Jog positions to decide where the mesh starts and ends


    yield from load_configuration("WAXSNEXAFS")

    yield from load_samp("OpenBeam")
    add_current_position_as_sample(name="OpenBeam", sample_id="OpenBeam")

    for polarization in [0, 90, 55]:
        print("Setting polarization: " + str(polarization))
        yield from set_polarization(polarization)

        for I0_position in I0_positions:
            print("Moving to izero_y position: " + str(I0_position))
            yield from bps.mv(izero_y, I0_position)

            energy_parameters = energy_list_parameters["carbon_NEXAFS"]
            yield from nbs_energy_scan(
                                *energy_parameters,
                                group_name="Assess different spots on I0 mesh",
                                sample="OpenBeam",
                                )
    

    yield from load_configuration("WAXSNEXAFS")
    


def gold_mesh_contamination_kinetics(iterations=1):

    template_acquisition = {
    "sample_id": "GoldGrid_AsIs",
    "configuration_instrument": "WAXSNEXAFS",
    "scan_type": "nexafs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [0],
    "cycles": 1,
    "group_name": "Monitor gold mesh contamination buildup",
    "priority": 1,
    }

    gold_mesh_queue = [template_acquisition]

    acquisition = copy.deepcopy(template_acquisition)
    acquisition["sample_id"] = "GoldGrid_UVO90min"
    acquisition["priority"] = gold_mesh_queue[-1]["priority"] + 1
    gold_mesh_queue.append(acquisition)

    ## Adding HOPG to generate some carbon contamination
    acquisition = copy.deepcopy(template_acquisition)
    acquisition["sample_id"] = "HOPG"
    acquisition["sample_angles"] = [20]
    acquisition["priority"] = gold_mesh_queue[-1]["priority"] + 1
    gold_mesh_queue.append(acquisition)


    ## Energy scans on gold mesh grids to assess rate of contamination formation
    for iteration in np.arange(0, iterations, 1):
        for acq in gold_mesh_queue:
            yield from run_acquisitions_single(acquisition=acq, dryrun=False)




def open_beam_waxs_photodiode_scans(iterations=1):

    """
    Purpose: 
    1. Check beam flux and normalized signal stability over time
    2. Check contamination level of upstream optics
    3. Run at polarizations below and above 90 degrees in an attempt to reproduce EPU errors and troubleshoot further.
    """


    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "WAXSNEXAFS",
    "scan_type": "nexafs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [0], #"polarizations": [0, 90, 45, 135], 
    "cycles": 0,
    "group_name": "Assess PGM contamination",
    "priority": 1,
    }

    open_beam_queue = [template_acquisition]

    for energy_parameters in ["nitrogen_NEXAFS", "oxygen_NEXAFS", "fluorine_NEXAFS"]:
        acquisition = copy.deepcopy(template_acquisition)
        acquisition["energy_list_parameters"] = energy_parameters
        acquisition["priority"] = open_beam_queue[-1]["priority"] + 1
        open_beam_queue.append(acquisition)
        
    

    ## Open beam scans to assess beam contamination
    ## Multiple iterations to fill time
    for iteration in np.arange(0, iterations, 1):
        for acq in open_beam_queue:
            yield from run_acquisitions_single(acquisition=acq, dryrun=False)



def open_beam_waxs_photodiode_scans_carbon(iterations=1):

    """
    Purpose: 
    1. Check beam flux and normalized signal stability over time
    2. Check contamination level of upstream optics
    3. Run at polarizations below and above 90 degrees in an attempt to reproduce EPU errors and troubleshoot further.
    """


    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "WAXSNEXAFS",
    "scan_type": "nexafs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [0, 90, 45, 135], 
    "cycles": 1,
    "group_name": "Assess PGM contamination",
    "priority": 1,
    }

    open_beam_queue = [template_acquisition]    

    ## Open beam scans to assess beam contamination
    ## Multiple iterations to fill time
    for iteration in np.arange(0, iterations, 1):
        for acq in open_beam_queue:
            yield from run_acquisitions_single(acquisition=acq, dryrun=False)



def zero_order_scans():
    ## Setting energy and polarization so that the EPU is at constant gap and phase
    yield from bps.mv(en.polarization, 90)
    yield from bps.mv(en, 291.65)
    yield from bps.mv(mirror2, -4)
    yield from bps.mv(grating, -4)

    ## Start and end at safe configuraiton like WAXSNEXAFS
    yield from load_configuration("WAXSNEXAFS")

    angles_optics = np.arange(-4, -1.3, 0.2)

    for sample_id in ["HOPG_new", "OpenBeam"]:
        yield from load_samp(sample_id)
        yield from rotate_now(20)

        for angle_optics in angles_optics:
            yield from bps.mv(grating, angle_optics)
            yield from bps.mv(mirror2, angle_optics)

            grating_angles_to_scan = np.linspace(
                start = angle_optics - 0.08,
                stop = angle_optics + 0.08,
                num = 100,
                                                )
            
            comment_template = "RSoXS 250 grating 0 order scans.  "
            comment_template = comment_template + "M2 = PGM = " + str(angle_optics) + " degrees. "
            comment_template = comment_template + str(sample_id) + ".  "

            yield from nbs_list_scan(
                grating,
                grating_angles_to_scan,
                comment = comment_template,
            )
        


    ## Restore energy
    yield from bps.mv(en.polarization, 90)
    yield from bps.mv(en, 291.65)



def HOPG_energy_resolution_series():
    """
    This series is especially helpful when selecting slits1.vsize to balance beam flux and energy resolution.
    Moreover, it should be run routinely during commissioning to assess energy resolution and adjust energy calibration if needed.
    """

    print("Starting HOPG energy resolution series")
    
    ## Start and end at safe configuraiton like WAXSNEXAFS
    yield from load_configuration("WAXSNEXAFS")

    ## Set polarization and energy parameters
    yield from set_polarization(90)
    energy_parameters = energy_list_parameters["carbon_NEXAFS"]

    yield from bps.mv(
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )

    slit1_vsizes = [0.01, 0.02, 0.04, 0.1, 0.2, 0.4]
    """
    slit1_vsizes = np.concatenate(
        (
            np.arange(0.01, 0.1, 0.005),
            np.arange(0.1, 1, 0.05),
            np.arange(1, 10, 0.5),
        )
    )
    """

    
    for sample_id in ["HOPG_new"]:
        ## Load sample at the desired angle
        print("Loading sample: " + str(sample_id))
        yield from load_samp(sample_id)
        yield from rotate_now(20)

        for slit1_vsize in slit1_vsizes:
            yield from bps.mv(slits1.vsize, slit1_vsize)
            yield from nbs_energy_scan(
                                        *energy_parameters,
                                        use_2d_detector=False, 
                                        dwell=1,
                                        n_exposures=1, 
                                        group_name="EnergyResolutionSeries",
                                        )


    yield from load_configuration("WAXSNEXAFS")



def WAXS_camera_position_offset_scans():

    print("Starting WAXS camera offset scans")

    ## SBA-15 scans with WAXS camera moved to different positions
    ## To decouple sample features from camera quadrant boundaries
    yield from load_configuration("WAXS") 

    ## Load SBA-15 sample.  This sample will stay in the same position throughout all scans.
    yield from load_samp("SBA15")
    
    ## Trying different polarizations in case SBA-15 has some anisotropy
    #for polarization in [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180]:
    #for polarization in [0, 90, 180, 45, 135, 15, 30, 60, 75, 105, 120, 150, 165]:
    for polarization in [0, 90, 45, 135]:
        yield from set_polarization(polarization)

        ## Iterate through different WAXS camera positions
        ## The WAXS camera comes in diagonally, so it would move both to the side and further from the sample.
        for waxs_detector_position in np.arange(2, -20, -2):
            yield from bps.mv(Det_W, waxs_detector_position)

            ## Run an energy scan going from 100 eV to 1000 eV in 100 eV increments
            ## Running 50 repeat exposures at each energy at 0.1 s exposure time each.
            energy_parameters = (200, 91.65, 291.65, 8.35, 300, 100, 1300)
            yield from nbs_energy_scan(
                                *energy_parameters,
                                use_2d_detector=True, 
                                dwell=0.1,
                                n_exposures=1, ## Was going to take 90 repeats, but then darks would be very infrequent 
                                group_name="Assess WAXS camera quadrants",
                                sample="SBA15",
                                )


def WAXS_camera_flat_field_illumination_Al_foil():

    ## Load WAXSNEXAFS with camera retracted, but I want all the SDD and other parameters to be as if it were with camera in beam path because I am taking camera images.
    yield from load_configuration("WAXSNEXAFS")
    mdToUpdate = {
            "RSoXS_Config": "WAXSNEXAFS",
            "RSoXS_Main_DET": "WAXS",
            "RSoXS_WAXS_SDD": 34.34,  # "RSoXS_WAXS_SDD": 39.19,
            "RSoXS_WAXS_BCX": 467.5,
            "RSoXS_WAXS_BCY": 513.4,
            "WAXS_Mask": [(367, 545), (406, 578), (880, 0), (810, 0)],
            "RSoXS_SAXS_SDD": None,
            "RSoXS_SAXS_BCX": None,
            "RSoXS_SAXS_BCY": None,
        }
    bl.md.update(mdToUpdate)


    yield from load_samp("AlFoil")
    yield from bps.mv(manipulator.r, -70) ## I don't want to do rotate_now because I want it to rotate in the other direction
    add_current_position_as_sample(name="AlFoil", sample_id="AlFoil")

    yield from set_polarization(0)

    ## Run at 800, 900, and 1000 eV
    ## Running 50 repeat exposures at each energy at 1 s and 5 s exposure time each.
    energy_parameters = (800, 100, 1000)
    yield from nbs_energy_scan(
                        *energy_parameters,
                        use_2d_detector=True, 
                        dwell=1,
                        n_exposures=50, ## Was going to take 90 repeats, but then darks would be very infrequent 
                        group_name="Assess WAXS camera quadrants using flat-field illumination",
                        sample="AlFoil",
                        )
    yield from nbs_energy_scan(
                        *energy_parameters,
                        use_2d_detector=True, 
                        dwell=5,
                        n_exposures=50, ## Was going to take 90 repeats, but then darks would be very infrequent 
                        group_name="Assess WAXS camera quadrants using flat-field illumination",
                        sample="AlFoil",
                        )
    



def WAXS_camera_flat_field_illumination_SiN():

    yield from load_configuration("WAXS")

    yield from load_samp("SiN_Blank")
    add_current_position_as_sample(name="SiN_Blank", sample_id="SiN_Blank")

    ## Trying different polarizations in case SBA-15 has some anisotropy
    for polarization in [0, 90, 45, 135]:
        yield from set_polarization(polarization)

        ## Run an energy scan going from 100 eV to 1000 eV in 100 eV increments
        ## Running 50 repeat exposures at each energy at 1 s exposure time each.
        energy_parameters = (440, 120, 560)
        yield from nbs_energy_scan(
                            *energy_parameters,
                            use_2d_detector=True, 
                            dwell=1,
                            n_exposures=50, ## Was going to take 90 repeats, but then darks would be very infrequent 
                            group_name="Assess WAXS camera quadrants using flat-field illumination",
                            sample="SiN_Blank",
                            )
        yield from nbs_energy_scan(
                            *energy_parameters,
                            use_2d_detector=True, 
                            dwell=5,
                            n_exposures=50, ## Was going to take 90 repeats, but then darks would be very infrequent 
                            group_name="Assess WAXS camera quadrants using flat-field illumination",
                            sample="SiN_Blank",
                            )




def WAXS_camera_energy_polarization_series(iterations=1):


    template_acquisition = {
    "sample_id": "SBA15",
    "configuration_instrument": "WAXS",
    "scan_type": "rsoxs",
    "energy_list_parameters": [291.65, 8.35, 300, 100, 400, 100, 500, 100, 600],
    "polarizations": [0, 90, 45, 135],
    "exposure_time": 0.1,
    "exposures_per_energy": 50,
    "group_name": "WAXS camera characterization",
    "priority": 1,
    }

    queue = [template_acquisition]    

    for iteration in np.arange(0, iterations, 1):
        for acq in queue:
            yield from run_acquisitions_single(acquisition=acq, dryrun=False)
    
    

## Just copied from Eliot's code
def do_cdsaxs(energies, samples):
    ## If a reduction in X-ray dose is needed, then adjust the slitsc aperture size and not the exposure time.  The 9 s exposure time is necessary to ensure X-ray exposure is delivered at all angles.
    yield from bps.mv(slitsc,-1.05) # big flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-57,end_angle=-80,exp_time=9,md={'plan_name':f'CD_high_{energy}'})
    yield from bps.mv(slitsc,-0.05) # mid flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-57,end_angle=-80,exp_time=9,md={'plan_name':f'CD_mid1_{energy}'})
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-65,end_angle=-88,exp_time=9,md={'plan_name':f'CD_mid2_{energy}'})
    yield from bps.mv(slitsc,-0.01) # least flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-65,end_angle=-88,exp_time=9,md={'plan_name':f'CD_low_{energy}'})
    yield from bps.mv(slitsc,-3.05) # all flux
    for samp in samples:
        yield from load_samp(samp)
        yield from bps.mv(sam_Th,-70)
        yield from do_rsoxs(edge=energies,frames=1,exposure=.1,md={'plan_name':f'CD_20deg'})


def do_just_rsoxs(energies, samples):
    """
    In case the do_rsoxs portion of do_cdsaxs fails.
    """
    yield from bps.mv(slitsc,-3.05) ## all flux
    for samp in samples:
        yield from load_samp(samp)
        yield from bps.mv(sam_Th, -70)
        yield from do_rsoxs(
            edge = energies, 
            frames = 1,
            exposure = 0.1,
            md = {"plan_name": f"CD_20deg", "RSoXS_Main_DET": "WAXS"},
            )
        

def do_cdsaxs_position_sweep():

    #yield from load_configuration("WAXS")
    #yield from bps.mv(Det_W, -50)
    yield from set_polarization(90) ## So that there is no rotation dependence
    energies = [270, 285, 290, 317, 323, 327, 330, 332, 345, 375, 383, 386, 403.5, 404.5, 410, 414, 418.5, 430, 505, 513, 517, 522, 531, 537.8, 539.5, 549, 551, 555]

    original_x_ZnMIPdeveloped = -1.20996394563853
    original_x_ZnMIPundeveloped = -1.2098320088991228
    #offsets = [-0.5, 0.5, -1, 1, -1.5, 1.5, -2, 2, -2.5, 2.5, -3, 3, -3.5, 3.5, -4, 4, -4.5, 4.5, -5, 5]
    offsets = [0.5, -1, 1, -1.5, 1.5, -2, 2, -2.5, 2.5, -3, 3, -3.5, 3.5, -4, 4, -4.5, 4.5, -5, 5]

    for offset in offsets[8:]:
        rsoxs_config["bar"][5]["location"][0]["position"] = original_x_ZnMIPdeveloped + offset
        sync_rsoxs_config_to_nbs_manipulator()

        yield from do_cdsaxs(energies, [5])
    
    
    for offset in offsets:
        rsoxs_config["bar"][6]["location"][0]["position"] = original_x_ZnMIPundeveloped + offset
        sync_rsoxs_config_to_nbs_manipulator()

        yield from do_cdsaxs(energies, [6])

    

def sdd_cdsaxs():
    yield from bps.mv(slitsc,-3.05)
    
    ## Run SBA15 at end to get SDD
    yield from load_samp("SBA15")
    #energy_parameters = (100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 1000)
    energy_parameters = (700, 100, 1000)
    yield from nbs_energy_scan(
                        *energy_parameters,
                        use_2d_detector=True, 
                        dwell=0.1,
                        group_name="SDD",
                        )
