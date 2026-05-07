import numpy as np
import copy
import datetime

import bluesky.plan_stubs as bps

from nbs_bl.plans.scans import nbs_count, nbs_list_scan, nbs_energy_scan
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.hw import (
    en,
    mir1,
    fs1_cam,
    fs6_cam,
    fs6_y,
    mirror2,
    grating,
    mir3,
    fs7_cam,
    slitsc,
    sst_control,
    slits1,
    izero_cam,
    izero_y,
    slits2,
    slits3,
    manipulator,
    sam_X,
    sam_Th,
    #waxs_det,
    #Det_W,
    fs13_cam,
    dm7_y,
)

from ..run_engine import md ## TODO: Is there a better way to do this?
from rsoxs.configuration_setup.configurations_instrument import load_configuration
from rsoxs.Functions.alignment import (
    #load_configuration, 
    load_samp, 
    rotate_now
    )
from rsoxs.HW.energy import set_polarization
from ..alignment.m3 import *
from ..alignment.energy_calibration import *
from .cdsaxs import cdsaxs_scan





def beam_time_startup():
    """
    Automates steps taken during beam time startup so that wiki will not have to be referred to, and steps will not have to be done separately and manually.
    """

    
    print("The currently active proposal is ")
    ## TODO: Is there a better way to do this than calling RE.md?
    print("proposal_id: " + str(md["proposal"]["proposal_id"]))
    print("title: " + str(md["proposal"]["title"]))
    print("pi_name: " + str(md["proposal"]["pi_name"]))
    print("\n")
    print("Is this the correct proposal? (y/n)")
    authenticated = input()
    if authenticated != "y": 
        ## TODO: Put instructions for using the GUI once the commissioning/GU proposal transition is fixed
        print("Please authenticate into the correct beam time proposal using sync-experiment.")
        print("To authenticate, open a new tab in the terminal and run the following command: ")
        print("sync-experiment -b SST1 -e rsoxs -p YOUR_PROPOSAL_NUMBER")
        print("You will be prompted for a username and password.  At the moment, a two-factor authentication push notification is not sent, but this may change.")
        ## -b is for beamline, -e is for endstation, -p is for proposal number
        ## The verbosity can be defined at the end of the command as needed (e.g., -v --verbose, -v --no-verbose)
        return
    
    print("Have you obtained confirmation from other SST staff and/or prior users that they are not using the soft beam? (y/n)")
    soft_beam_not_being_used = input()
    if soft_beam_not_being_used != "y":
        print("Please check that the soft beam is not being used to avoid disrupting someone else's measurement.")

    
    ## TODO: make new device, e.g., select_active_end_station, which has _target = ophyd.EpicsSignal, not EpicsSignalRO, so that I could change to RSoXS
    ## TODO: use select_active_end_station.set("RSoXS") instead of yield from bps.mv(sst_control, "RSoXS")
    ## Latter will use RE, but we have a suspender if RSoXS is not the active station
    #print("Changing active endstation to RSoXS.")
    #yield from bps.mv(sst_control, "RSoXS")

    ## TODO: Probably have separate functions for changing grating and loading safe RSoXS configuration
    ## TODO: For changing the grating, probably want to ultimately edit the grating_to_rsoxs function in sst_base directly, but test here first.
    ## Want to have it check O2 bleed levels before making any movements.
    
    ## TODO: automate protocol outlined here: https://wiki-nsls2.bnl.gov/beamline7ID1/index.php?title=Beam_time_workflow_and_Bluesky_guide#Beam_time_startup




def test_scans_prefect():
    """
    Prefect is used to write out 1D detector data to csv files and 2D detector data to tiff files.
    The scans in this function will be used to test if the workflows are correctly writing out files.

    """

    comment = "Test scan to ensure data is written out by Prefect."

    ## Test scan where multiple darks are taken in one scan
    sam_X_to_scan = np.arange(0, 0.3, 0.1)
    yield from nbs_list_scan(sam_X, sam_X_to_scan, use_2d_detector=True, dwell=1, n_exposures=1, comment=comment)

    ## Test scan with repeat exposures on CCD
    yield from nbs_count(
        use_2d_detector = True,
        num = 3,
        n_exposures = 3,
        dwell = 1,
        comment = comment,
        )
    
    ## Test scans with CCD without repeat exposures
    yield from nbs_count(
        use_2d_detector = True,
        num = 3,
        n_exposures = 1,
        dwell = 1,
        comment = comment,
        )
    
    ## Test scans without CCD
    yield from nbs_count(
        use_2d_detector = False,
        num = 3,
        n_exposures = 1,
        dwell = 1,
        comment = comment,
        )



def commissioning_scans_20260406():

    comment = "SRS570 sensitivities: I0 = 1 nA/V, TEY = 100 pA/V, WAXS photodiode = 10 nA/V"

    
    for iteration in np.arange(0, 1, 1):
        for polarization in [90]: #[0, 90, 45, 135]:
            yield from set_polarization(polarization)

            yield from load_samp("OpenBeam_HOPG")
            yield from nbs_energy_scan(250, 1.28, 282, 0.3, 297, 1.325, 350, comment = comment)
            yield from nbs_energy_scan(370, 1, 397, 0.2, 407, 1, 440, comment = comment)
            yield from nbs_energy_scan(500, 1, 525, 0.2, 540, 1, 560, comment = comment)
            yield from nbs_energy_scan(650, 1.5, 680, 0.25, 700, 1.25, 740, comment = comment)

    




def commissioning_scans_20260328():

    comment = "SRS570 sensitivities: I0 = 100 pA/V, TEY = 20 pA/V, DM7 photodiode = 200 nA/V"


    energies_250grating_default = np.concatenate((
        np.array([90, 110, 130, 150, 200, 250]),
        np.arange(300, 1100, 100)
    ))
    energies_1200grating_default = np.concatenate((
        energies_250grating_default,
        np.arange(1100, 2100, 100)
    ))
    m3_pitches_to_scan = np.arange(7.6, 8, 0.002)
    m3_xs = np.arange(24, 24.5, 0.05)
    yield from m3_sweep(
            polarizations = [90, 0],
            energies = energies_1200grating_default,
            m3_xs = m3_xs,
            m3_pitches = m3_pitches_to_scan,
            configuration = "DM7NEXAFS",
            sample_id = "OpenBeam",

    )

    print("Starting open-beam energy scans")
    yield from load_configuration("DM7NEXAFS")
    for iteration in np.arange(0, 1000, 1):
        for polarization in [0, 90, 45, 135]:
            yield from set_polarization(polarization)

            yield from load_samp("OpenBeam")
            yield from nbs_energy_scan(250, 1.28, 282, 0.3, 297, 1.325, 350, comment = comment)
            yield from nbs_energy_scan(370, 1, 397, 0.2, 407, 1, 440, comment = comment)
            yield from nbs_energy_scan(500, 1, 525, 0.2, 540, 1, 560, comment = comment)
            yield from nbs_energy_scan(650, 1.5, 680, 0.25, 700, 1.25, 740, comment = comment)
    













## Custom scripts for commissioning #################################
## Moved over from run_acquisitions, so need to make sure all devices are imported.




    






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




def beam_motion_monitoring_20260312(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Set up configuration
    yield from bps.mv(mir1.x, 1.3)
    yield from bps.mv(fs6_y, 1.5)
    yield from bps.mv(mir3.x, 24.2)
    yield from bps.mv(mir3.pitch, 7.78)
    yield from load_configuration("DM7_FluorescenceImage")
    ## Open all slits to get big beam
    yield from bps.mv(
        slits1.vsize, 10,
        slits1.hsize, 10,
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)
    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]


    for iteration in np.arange(0, 1000000, 1):

        ## FS13
        yield from load_configuration("DM7_FS13")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs13_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs13_cam],
            )
        ## Without I0 to see if we get streaky image
        yield from load_configuration("DMRSoXS_Retracted")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs13_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs13_cam],
            )
        
        
        ## FSRSoXS
        yield from load_configuration("DMRSoXS_FluorescenceScreen")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [izero_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [izero_cam],
            )
        

        ## FS7
        yield from bps.mv(mir3.x, 0)
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs7_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs7_cam],
            )
        

        ## FS6
        yield from bps.mv(fs6_y, -17)
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs6_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs6_cam],
            )
        
        
        ## FS1
        yield from bps.mv(mir1.x, -5)
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs1_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs1_cam],
            )



        ## Restore all configurations
        yield from bps.mv(mir1.x, 1.3)
        yield from bps.mv(fs6_y, 1.5)
        yield from bps.mv(mir3.x, 24.2)
        yield from load_configuration("DMRSoXS_Mesh")
    


    yield from load_configuration("DM7_FluorescenceImage")



def beam_motion_monitoring_20260313(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Set up configuration
    yield from bps.mv(mir1.x, 1.3)
    yield from bps.mv(fs6_y, 1.5)
    yield from bps.mv(mir3.x, 24.2)
    yield from bps.mv(mir3.pitch, 7.78)
    yield from load_configuration("DM7_FluorescenceImage")
    ## Open all slits to get big beam
    yield from bps.mv(
        slits1.vsize, 10,
        slits1.hsize, 10,
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)
    #energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 1000]


    for iteration in np.arange(0, 1000000, 1):

        ## FS13
        yield from load_configuration("DM7_FS13")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs13_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs13_cam],
            )
        ## Without I0 to see if we get streaky image
        yield from load_configuration("DMRSoXS_Retracted")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs13_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs13_cam],
            )
        
        
        ## FSRSoXS
        yield from load_configuration("DMRSoXS_FluorescenceScreen")
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [izero_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [izero_cam],
            )
     

        ## Restore all configurations
        yield from load_configuration("DMRSoXS_Mesh")
    


    yield from load_configuration("DM7_FluorescenceImage")





def beam_motion_monitoring_20260313_2(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Set up configuration
    yield from load_configuration("DM7_FluorescenceImage")
    yield from bps.mv(mir3.x, 0)

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)
    #energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 1000]


    for iteration in np.arange(0, 1000000, 1):

        ## FS7
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs7_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs7_cam],
            )
    

    yield from bps.mv(mir3.x, 24.2)
    yield from bps.mv(mir3.pitch, 7.78)
    yield from load_configuration("DM7_FluorescenceImage")



def beam_motion_monitoring_FS1_20260216(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Retract M1 to access FS1
    yield from bps.mv(mir1.x, -5)

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)

    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    
    for cycle in np.arange(0, 1000000, 1):
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs1_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs1_cam],
            )
        







def beam_motion_monitoring_FS6_20260215(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Bring in FS6
    ## TODO: make device for FS6

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)

    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    
    for cycle in np.arange(0, 1000000, 1):
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs6_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs6_cam],
            )
        


def beam_motion_monitoring_FS7_20260214(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Retract M3 to access FS7
    yield from bps.mv(mir3.x, 0)

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)

    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    
    for cycle in np.arange(0, 1000000, 1):
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs7_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs7_cam],
            )
        


def beam_motion_monitoring_FS13_20260213(
        sample_id = "OpenBeam",
):
    """
    Quick function to get started while I put together a more detailed one below.
    """

    ## Open all slits to get big beam
    yield from bps.mv(
        slits1.vsize, 10,
        slits1.hsize, 10,
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )
    yield from bps.mv(dm7_y, -42)

    yield from load_samp("OpenBeam")

    yield from set_polarization(0)

    energy_parameters = [100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 2000]
    
    for cycle in np.arange(0, 1000000, 1):
        yield from nbs_energy_scan(
            *energy_parameters,
            extra_dets = [fs13_cam],
            )
        yield from nbs_energy_scan(
            *energy_parameters[::-1], ## Reverse the energy list parameters to produce reversed energy list
            extra_dets = [fs13_cam],
            )


def beam_motion_monitoring(
        sample_id = "OpenBeam",
):
    """
    Repeated energy scans will be performed to assess beam motion.
    Energy sweep reveals if beam moves with energy.
    Extracting specified energy over time reveals if beam moves with time.
    """

    yield from load_configuration("DM7_FS13")

    yield from load_samp("OpenBeam")






def I0_mesh_vertical_profile_energy_scan():


    
    ## Full scan set
    I0_positions = np.arange(-42.8, -24, 0.2) ## TODO: Jog positions to decide where the mesh starts and ends


    yield from load_configuration("WAXSNEXAFS")

    yield from load_samp("HOPG_guess") #yield from load_samp("OpenBeam")

    for polarization in [0, 90, 55]:
        print("Setting polarization: " + str(polarization))
        yield from set_polarization(polarization)

        for I0_position in I0_positions:
            
            #if polarization == 90 and I0_position < -38.7: continue
            
            print("Moving to izero_y position: " + str(I0_position))
            yield from bps.mv(izero_y, I0_position)

            energy_parameters = energy_list_parameters["carbon_NEXAFS"]
            yield from nbs_energy_scan(
                                *energy_parameters,
                                group_name="Assess different spots on I0 mesh",
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

    for energy_parameters in ["nitrogen_NEXAFS", "oxygen_NEXAFS", "fluorine_NEXAFS", "silicon_NEXAFS"]:
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




"""
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
"""

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
    
    waxs_det = bl["waxs_det"]
    
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
        #yield from do_rsoxs(edge=energies,frames=1,exposure=.1,md={'plan_name':f'CD_20deg'})
        ## TODO: Below needs testing, but getting rid of do_rsoxs
        
        ## Creating energy parameters list that works with nbs scans
        energy_parameters = [energies[0]]
        for energy in energies[1:]:
            energy_parameters.extend([
                (energy - energy_parameters[-1]), ## Step size
                energy, ## Energy region end point
            ])

        yield from nbs_energy_scan(
            *energy_parameters,
            use_2d_detector = True,
            dwell = 0.1,
            comment = f'CD_20deg',
        )


def do_just_rsoxs(energies, samples):
    """
    In case the do_rsoxs portion of do_cdsaxs fails.
    """
    yield from bps.mv(slitsc,-3.05) ## all flux
    for samp in samples:
        yield from load_samp(samp)
        yield from bps.mv(sam_Th, -70)
        """
        yield from do_rsoxs(
            edge = energies, 
            frames = 1,
            exposure = 0.1,
            md = {"plan_name": f"CD_20deg", "RSoXS_Main_DET": "WAXS"},
            )
        """
        ## TODO: Below needs testing, but getting rid of do_rsoxs

        ## Creating energy parameters list that works with nbs scans
        energy_parameters = [energies[0]]
        for energy in energies[1:]:
            energy_parameters.extend([
                (energy - energy_parameters[-1]), ## Step size
                energy, ## Energy region end point
            ])

        yield from nbs_energy_scan(
            *energy_parameters,
            use_2d_detector = True,
            dwell = 0.1,
            comment = f'CD_20deg',
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

        