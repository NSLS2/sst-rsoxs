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
    slits_foe,
    fs6_cam,
    mirror2,
    grating,
    mir3,
    fs7_cam,
    slitsc,
    slits1,
    izero_y,
    slits2,
    slits3,
    manipulator,
    sam_X,
    sam_Y,
    sam_Th,
    #waxs_det,
    Det_W,
    fs13_cam,
    dm7_y,
)


from rsoxs.configuration_setup.configurations_instrument import load_configuration
from rsoxs.Functions.alignment import (
    #load_configuration, 
    load_samp, 
    rotate_now
    )
from rsoxs.HW.energy import set_polarization
from ..alignment.m3 import *
from ..alignment.energy_calibration import *
from .run_acquisitions import run_acquisitions_single







def night_20260328():
    """
    """

    ## Low flux NEXAFS with broadband beam
    ## TODO: if intensities are too low, use repeat exposures
    print("Starting low flux NEXAFS scans with broadband beam")
    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "WAXS_BroadbandReflectivity",
    "scan_type": "rsoxs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [90], 
    "cycles": 1,
    "group_name": "Low flux NEXAFS with broadband beam",
    "priority": 1,
    }
    queue = []
    for sample_id in [
        "OpenBeam", 
        "SiN_Blank", 
        "50nmPS", 
        "25nmPS",
        "OpenBeam", 
        "SiN_Blank",
        ]:
        acquisition = copy.deepcopy(template_acquisition)
        acquisition["sample_id"] = sample_id
        queue.append(acquisition)
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)
    print("With I0 mesh")
    for acquisition in queue:
        acquisition["configuration_instrument"] = "WAXS_BroadbandReflectivity_withI0Mesh"
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)


    ## Low flux NEXAFS with monochromatic beam
    ## TODO: if intensities are too low, use repeat exposures
    print("Starting low flux NEXAFS scans with monochromatic beam")
    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "WAXS_LowFluxNEXAFS",
    "scan_type": "rsoxs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [90], 
    "cycles": 1,
    "group_name": "Low flux NEXAFS with monochromatic beam",
    "priority": 1,
    }
    queue = []
    for sample_id in [
        "OpenBeam", 
        "SiN_Blank", 
        "50nmPS", 
        "25nmPS",
        "OpenBeam", 
        "SiN_Blank",
        ]:
        acquisition = copy.deepcopy(template_acquisition)
        acquisition["sample_id"] = sample_id
        queue.append(acquisition)
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)
    print("With I0 mesh")
    for acquisition in queue:
        acquisition["configuration_instrument"] = "WAXS_LowFluxNEXAFS_withI0Mesh"
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)


    ## Spirals
    print("Starting spirals with monochromatic beam")
    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "WAXS_LowFluxNEXAFS",
    "scan_type": "spiral",
    "energy_list_parameters": 270,
    "polarizations": [90], 
    "spiral_dimensions": [0.2, 3, 3],
    "group_name": "Spirals with monochromatic beam",
    "priority": 1,
    }
    queue = []
    for sample_id in [
        "SiN_Blank", 
        "50nmPS", 
        "25nmPS",
        ]:
        acquisition = copy.deepcopy(template_acquisition)
        acquisition["sample_id"] = sample_id
        queue.append(acquisition)
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)


    
    
    ## End in safe configuration
    yield from load_configuration("DM7NEXAFS")
    yield from load_samp("OpenBeam")





def night_20260327():
    """
    """

    ## Standard NEXAFS
    print("Starting NEXAFS scans")
    template_acquisition = {
    "sample_id": "OpenBeam",
    "configuration_instrument": "DM7NEXAFS",
    "scan_type": "nexafs",
    "energy_list_parameters": "carbon_NEXAFS",
    "polarizations": [90], 
    "cycles": 1,
    "group_name": "Standard NEXAFS",
    "priority": 1,
    }
    queue = []
    for sample_id in [
        "OpenBeam", 
        "SiN_Blank", 
        "50nmPS", 
        "25nmPS",
        "PS_TEY",
        "HOPG",
        "OpenBeam", 
        "SiN_Blank",
        ]:
        acquisition = copy.deepcopy(template_acquisition)
        acquisition["sample_id"] = sample_id
        if sample_id == "PS_TEY" or sample_id == "HOPG":
            acquisition["sample_angles"] = [20]
        queue.append(acquisition)
    for acq in queue:
        yield from run_acquisitions_single(acquisition=acq, dryrun=False)
    


    ## Find q range across different detector positions
    ## Does moving the detector out actually give larger q?
    print("Starting WAXS camera offset scans")
    yield from load_configuration("WAXS") 
    ## Load SBA-15 sample.  This sample will stay in the same position throughout all scans.
    yield from load_samp("SBA15")
    ## Iterate through different WAXS camera positions
    ## The WAXS camera comes in diagonally, so it would move both to the side and further from the sample.
    for waxs_detector_position in np.arange(2, -94, -8):
        yield from bps.mv(Det_W, waxs_detector_position)
        energy_parameters = (100, 100, 200, 91.65, 291.65, 8.35, 300, 100, 1300)
        yield from nbs_energy_scan(
                            *energy_parameters,
                            use_2d_detector=True, 
                            dwell=0.1,
                            n_exposures=1, 
                            )
    
    ## End in safe configuration
    yield from load_configuration("DM7NEXAFS")
    yield from load_samp("OpenBeam")
        
    
    ## Spiral scans







def night_20260220():
    """
    """

    """
    ## Fluorescence screen images of beam cut down by FOE slits
    ## FE slits hsize and vsize = 0 for all these scans
    ## Notes for 20260220 night...do a series wehre we start open adn close of towards the targets below
    ## FE slits hsize = 0.1, vsize = 4 to see tall beam
    ## FOE slits vsize = 10, vcenter = 0, hsize = 0, hcenter = 2.1
    ## slits 2 hsize = 0.15 --> no need because the lobes go away after pulling out I0 mesh
    comment = "Visualizing how beam is cut down.  "
    comment += "FE slits hsize = 0.1 and vsize = 4.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "
    yield from load_samp("OpenBeam") ## Load sample
    yield from set_polarization(90) ## p polarization
    ## FE slits hsize = 0.1, vsize = 4 to see tall beam
    yield from load_configuration("DM7_FluorescenceImage_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from bps.mv(slits1.vsize, 10, slits1.hsize, 10, slits2.vsize, 10, slits2.hsize, 10, slits3.vsize, 10, slits3.hsize, 10)
    energy_parameters = (285, 6.65, 291.65)
    slits_foe_hsizes_to_scan = np.arange(6, -0.1, -0.1)
    for slits_foe_hsize in slits_foe_hsizes_to_scan:
        yield from bps.mv(slits_foe.hsize, slits_foe_hsize)
        yield from nbs_energy_scan(
                                    *energy_parameters,
                                    extra_dets = [fs13_cam],
                                    dwell=1,
                                    comment = comment,
                                    )
    yield from load_configuration("DM7_FluorescenceImage_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from bps.mv(slits1.vsize, 10, slits1.hsize, 10, slits2.vsize, 10, slits2.hsize, 10, slits3.vsize, 10, slits3.hsize, 10)
    """
    
    
    


    ## CFF series with images
    comment = "Trying to focus beam on fluorescence screen and get spectrum across vertical cut.  "
    comment += "FE slits hsize and vsize = 1.5.  " 
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    ## FE slits hsize = 1.5, vsize = 1.5
    yield from load_configuration("DM7_FluorescenceImage_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    yield from bps.mv(en, 285) ## Where PS has sharpest resonance

    cffs_to_scan = (1.5, 2.5, 0.05) ## Didn't find proper limits, so I'll try this range for now.

    for sample_id in ["ps_50nm", "ps_25nm"]:
        yield from load_samp(sample_id)
        
        yield from nbs_list_scan(
            en.monoen.cff,
            cffs_to_scan, 
            extra_dets = [fs13_cam],
            dwell=1,
            comment=comment,
            ) 
    
    yield from load_configuration("DM7_FluorescenceImage_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    yield from bps.mv(en, 285) ## Where PS has sharpest resonance
    yield from bps.mv(en.monoen.cff, 1.7)



    ## CFF series with nexafs scans
    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization

    comment = "PS NEXAFS at different CFFs.  "
    comment += "FE slits hsize and vsize = 1.5.  " 
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    energy_parameters = (250, 1.28, 282, 0.3, 297, 1.325, 350)

    for cff in cffs_to_scan:
        yield from bps.mv(en.monoen.cff, cff)

        for sample_id in ["blank_window", "ps_50nm", "ps_25nm"]:
            yield from load_samp(sample_id)
            yield from nbs_energy_scan(
                                    *energy_parameters,
                                    dwell=1,
                                    comment = comment,
                                    )

    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    yield from bps.mv(en.monoen.cff, 1.7)


    ## Testing for repeat characters!!! woohoo!
    ## knife edge without I0

    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    yield from load_samp("OpenBeam")

    comment = "Knife edge with bottom of bar with no I0 mesh.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    sam_Y_to_scan = np.arange(10, 5.45, -0.05)
    yield from nbs_list_scan(
        sam_Y, 
        sam_Y_to_scan, 
        comment=comment,
        )
    
    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    yield from load_samp("OpenBeam")

    comment = "Knife edge with slit 3 outboard blade with no I0 mesh.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    slits3_outboard_to_scan = np.arange(5.2, -1, -0.05)
    yield from nbs_list_scan(
        slits3.outboard, 
        slits3_outboard_to_scan, 
        comment=comment,
        )
    
    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization
    
    comment = "Knife edge with PS transmission samples with no I0.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    sample_id = "ps_50nm"
    yield from load_samp(sample_id)
    sam_Y_to_scan = np.arange(-38.8, -34.8, 0.05)
    yield from nbs_list_scan(
        sam_Y, 
        sam_Y_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)
    sam_X_to_scan = np.arange(-0.5, 3.5, 0.05)
    yield from nbs_list_scan(
        sam_X, 
        sam_X_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)

    sample_id = "ps_25nm"
    yield from load_samp(sample_id)
    sam_Y_to_scan = np.arange(-38.6, -34.6, 0.05)
    yield from nbs_list_scan(
        sam_Y, 
        sam_Y_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)
    sam_X_to_scan = np.arange(-8, -4, 0.05)
    yield from nbs_list_scan(
        sam_X, 
        sam_X_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)



    ## NEXAFS at different positions
    yield from load_configuration("DM7NEXAFS_BroadbandReflectivity")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from set_polarization(90) ## p polarization

    comment = "NEXAFS scan at top/bottom edge of PS sample to gauge spread of energies at different regions of the beam.  "
    comment += "No I0 mesh in beam path.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    energy_parameters = (250, 1.28, 282, 0.3, 297, 1.325, 350)
    
    for sample_id in [
        "blank_window", 
        "ps_50nm_top", 
        "ps_50nm_bottom", 
        "ps_25nm_top", 
        "ps_25nm_bottom",
        "blank_window",
        ]:
        yield from load_samp(sample_id)

        yield from nbs_energy_scan(
                                    *energy_parameters,
                                    dwell=1,
                                    comment = comment,
                                    )









def knife_edge_20260220():
    """
    Transition from beam to no beam will be convolution of step function and shape of beam in direction of scan.
    """

    """
    comment = "Knife edge with bottom of bar.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    #sam_Y_to_scan = np.arange(10, 6, -0.05)
    sam_Y_to_scan = np.arange(6, 5.45, -0.05)
    yield from nbs_list_scan(
        sam_Y, 
        sam_Y_to_scan, 
        comment=comment,
        )
    """

    """
    ## Side of bar won't work maybe
    comment = "Knife edge with slit 3 outboard blade.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    yield from load_configuration("DM7_Photodiode")
    sample_id = "OpenBeam"
    yield from load_samp(sample_id)
    #slits3_outboard_to_scan = np.arange(5.2, -1, -0.2)
    slits3_outboard_to_scan = np.arange(3, -2, -0.05)
    yield from nbs_list_scan(
        slits3.outboard, 
        slits3_outboard_to_scan, 
        comment=comment,
        )
    """

    """
    comment = "Knife edge with ps_50nm.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    yield from load_configuration("DM7_Photodiode")
    sample_id = "ps_50nm"
    yield from load_samp(sample_id)
    sam_Y_to_scan = np.arange(-38.8, -34.8, 0.05)
    yield from nbs_list_scan(
        sam_Y, 
        sam_Y_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)
    sam_X_to_scan = np.arange(-10, 0, 0.2)
    yield from nbs_list_scan(
        sam_X, 
        sam_X_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)
    """

    comment = "NEXAFS scan at top/bottom edge of PS sample to gauge spread of energies at different regions of the beam.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    yield from load_configuration("DM7_Photodiode")
    yield from set_polarization(90)
    energy_parameters = (250, 1.28, 282, 0.3, 297, 1.325, 350)
    
    for sample_id in [
        "blank_window", 
        "ps_50nm_top", 
        "ps_50nm_bottom", 
        "ps_25nm_top", 
        "ps_25nm_bottom",
        "blank_window",
        ]:
        yield from load_samp(sample_id)

        yield from nbs_energy_scan(
                                    *energy_parameters,
                                    dwell=1,
                                    comment = comment,
                                    )
        
    
    
    
    comment = "Knife edge with ps_50nm.  "
    comment += "FE slits hsize and vsize = 1.5.  "
    comment += "SRS570 sensitivities: DM7 photodiode sensitivity = 1 uA/V.  I0 sensitivity = 5 nA/V.  "

    sample_id = "ps_50nm"
    yield from load_samp(sample_id)
    sam_X_to_scan = np.arange(-0.5, 3.5, 0.05)
    yield from nbs_list_scan(
        sam_X, 
        sam_X_to_scan, 
        comment=comment,
        )
    yield from load_samp(sample_id)
        
    
    


    

    







def slit_sweeps_20260219(
        #sample_id = "HOPG_NIST",
):   
    """
    """

    """
    ## Load sample
    yield from load_samp(sample_id)

    ## Set polarization
    yield from set_polarization(90) ## p polarization

    ## Load configuration
    yield from load_configuration("DM7NEXAFS")
    
    #yield from bps.mv(
    #    slits_foe.hsize, 8, slits_foe.hcenter, -1,
    #    slits_foe.vsize, 10, slits_foe.vcenter, 0,
    #                  )
    
    yield from bps.mv(
        slits_foe.hsize, 6, slits_foe.hcenter, 2.1,
        slits_foe.vsize, 10, slits_foe.vcenter, 0,
                      )

    ## Open slits 2 and 3, as they are not needed for NEXAFS
    yield from bps.mv(
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )
    ## Open slits 1 to see extent of energies captured by FE slits
    yield from bps.mv(slits1.vsize, 10)
    yield from bps.mv(slits1.hsize, 10)


    energy_parameters = (280, 0.3, 310)

    yield from bps.mv(slits_foe.hsize, 0.1)
    yield from nbs_energy_scan(
                                *energy_parameters,
                                dwell=1,
                                comment = "FE slits vsize and hsize = 0"
                                )
    yield from bps.mv(slits_foe.vsize, 0.5)
    yield from nbs_energy_scan(
                                *energy_parameters,
                                dwell=1,
                                comment = "FE slits vsize and hsize = 0"
                                )
    """
    


    """
    yield from bps.mv(en, 291.65)
    
    yield from bps.mv(slits_foe.hsize, 0.1)
    slits_foe_hcenters_to_scan = np.arange(0, 3.5, 0.1)
    yield from nbs_list_scan(slits_foe.hcenter, slits_foe_hcenters_to_scan)

    yield from bps.mv(
        slits_foe.hsize, 8, slits_foe.hcenter, -1,
        slits_foe.vsize, 10, slits_foe.vcenter, 0,
                      )
    
    yield from bps.mv(slits_foe.vsize, 0.5)
    slits_foe_vcenters_to_scan = np.arange(-2.5, 1.5, 0.1)
    yield from nbs_list_scan(slits_foe.vcenter, slits_foe_vcenters_to_scan)
    """


    ## 20260219 night scans#################################################3

    ## Fluorescence screen images of beam cut down by FOE slits
    ## FE slits hsize and vsize = 0 for all these scans
    ## Notes for 20260220 night...do a series wehre we start open adn close of towards the targets below
    ## FE slits hsize = 0.1, vsize = 4 to see tall beam
    ## FOE slits vsize = 10, vcenter = 0, hsize = 0, hcenter = 2.1
    ## slits 2 hsize = 0.15
    yield from load_samp("OpenBeam") ## Load sample
    yield from set_polarization(90) ## p polarization
    yield from load_configuration("DM7_FluorescenceImage")
    yield from bps.mv(slits_foe.hsize, 6, slits_foe.hcenter, 2.1, slits_foe.vsize, 10, slits_foe.vcenter, 0)
    yield from bps.mv(slits1.vsize, 10, slits1.hsize, 10, slits2.vsize, 10, slits2.hsize, 10, slits3.vsize, 10, slits3.hsize, 10)
    energy_parameters = (285, 6.65, 291.65)
    slits_foe_hsizes_to_scan = np.arange(5.1, 0, -0.1)
    slits_foe_vsizes_to_scan = np.arange(9.5, 0, -0.5)
    for slits_foe_hsize in slits_foe_hsizes_to_scan:
        yield from bps.mv(slits_foe.hsize, slits_foe_hsize)
        for slits_foe_vsize in slits_foe_vsizes_to_scan:
            yield from bps.mv(slits_foe.vsize, slits_foe_vsize)
            yield from nbs_energy_scan(
                                        *energy_parameters,
                                        extra_dets = [fs13_cam],
                                        dwell=10,
                                        comment = "FE slits vsize and hsize = 0"
                                        )
            
    
    ## PS scans
    yield from set_polarization(90) ## p polarization
    energy_parameters = (280, 0.3, 310)
    for sample_id in ["ps_50nm", "ps_on_si", "ps_25nm"]:
        yield from load_samp(sample_id)

        yield from load_configuration("DM7NEXAFS")
        yield from bps.mv(slits_foe.hsize, 0.1, slits_foe.hcenter, 2.1, slits_foe.vsize, 0.5, slits_foe.vcenter, 0)
        yield from bps.mv(slits1.vsize, 10, slits1.hsize, 10, slits2.vsize, 10, slits2.hsize, 10, slits3.vsize, 10, slits3.hsize, 10)
        ## Probably clipping off beam by sample frame?
        yield from nbs_energy_scan(
                                *energy_parameters,
                                dwell=1,
                                comment = "FE slits vsize and hsize = 0"
                                )
        
        if sample_id != "ps_on_si":
            yield from load_configuration("DM7_FluorescenceImage")
            yield from bps.mv(slits_foe.hsize, 0.1, slits_foe.hcenter, 2.1, slits_foe.vsize, 0.5, slits_foe.vcenter, 0)
            yield from bps.mv(slits1.vsize, 10, slits1.hsize, 10, slits2.vsize, 10, slits2.hsize, 10, slits3.vsize, 10, slits3.hsize, 10)
            ## Probably clipping off beam by sample frame?
            yield from nbs_energy_scan(
                                    *energy_parameters,
                                    extra_dets = [fs13_cam],
                                    dwell=10,
                                    comment = "FE slits vsize and hsize = 0"
                                    )
    



    ## Restore old configuraitons
    yield from load_configuration("DM7NEXAFS")
    yield from bps.mv(
        slits_foe.hsize, 6, slits_foe.hcenter, 2.1,
        slits_foe.vsize, 10, slits_foe.vcenter, 0,
                      )


## Testing for repeat characters.  Testing foooooooooooooooooooooooooooooooooooooooooooooooooooooor repeat characters.
##################################################### 
## Testing for repeat characters