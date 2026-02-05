import numpy as np
import copy
import datetime

import bluesky.plan_stubs as bps

from nbs_bl.plans.scans import nbs_count, nbs_list_scan, nbs_energy_scan
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


from rsoxs.configuration_setup.configurations_instrument import load_configuration
from rsoxs.Functions.alignment import (
    #load_configuration, 
    load_samp, 
    rotate_now
    )
from rsoxs.HW.energy import set_polarization
from ..alignment.m3 import *






def commissioning_scans_20260204():

    
    #yield from HOPG_energy_resolution_series()

    yield from m3_sweep(sample_id = "OpenBeam_SolidY345")
    #yield from I0_mesh_vertical_profile_energy_scan()

    #yield from open_beam_waxs_photodiode_scans(iterations=1)
    yield from load_samp("OpenBeam_SolidY345")
    for iteration in np.arange(0, 1000, 1):
        for polarization in [0, 90, 45, 135]:
            yield from set_polarization(polarization)
            yield from nbs_energy_scan(250, 1.28, 282, 0.3, 297, 1.325, 350)
            yield from nbs_energy_scan(370, 1, 397, 0.2, 407, 1, 440)
            yield from nbs_energy_scan(500, 1, 525, 0.2, 540, 1, 560)
            yield from nbs_energy_scan(650, 1.5, 680, 0.25, 700, 1.25, 740)
            yield from nbs_energy_scan(1820, 1.25, 1840, 0.25, 1860, 1.25, 1910)
        