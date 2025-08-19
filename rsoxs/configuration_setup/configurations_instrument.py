import numpy as np

# from ..startup import RE
from nbs_bl.queueserver import GLOBAL_USER_STATUS
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
import bluesky.plan_stubs as bps
from nbs_bl.printing import run_report
from nbs_bl.hw import (
    mir1,
    en,
    mir3,
    psh10,
    slitsc,
    slits1,
    shutter_y,
    izero_y,
    slits2,
    slits3,
    Det_W,
    # Det_S,
    BeamStopS,
    BeamStopW,
    sam_Th,
    sam_Z,
    sam_Y,
    sam_X,
    TEMZ,
    #mir4OLD,
    # dm7
)

from ..HW.energy import mono_en, grating_to_1200

GLOBAL_CONFIGURATION_DICT = GLOBAL_USER_STATUS.request_status_dict("RSoXS_Config")


def load_configuration(configuration_name):
    print("Loading configuration: " + str(configuration_name))
    yield from move_motors(configuration_name)

    if "NEXAFS" in configuration_name:
        mdToUpdate = {
            "RSoXS_Config": configuration_name,
            "RSoXS_Main_DET": "beamstop_waxs",
            "RSoXS_WAXS_SDD": None,
            "RSoXS_WAXS_BCX": None,
            "RSoXS_WAXS_BCY": None,
            "RSoXS_SAXS_SDD": None,
            "RSoXS_SAXS_BCX": None,
            "RSoXS_SAXS_BCY": None,
        }
        bl.md.update(mdToUpdate)

    else:
        mdToUpdate = {
            "RSoXS_Config": configuration_name,
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


def move_motors(configuration_name):
    ## configuration is a string that is a key in the default_configurations dictionary
    configuration_setpoints = GLOBAL_CONFIGURATION_DICT[configuration_name]

    ## Sort by order
    configuration_setpoints_sorted = sorted(configuration_setpoints, key=lambda x: x["order"])

    ## Then move in that order
    for order in np.arange(0, int(configuration_setpoints_sorted[-1]["order"] + 1), 1):
        move_list = []
        for indexMotor, motor in enumerate(configuration_setpoints_sorted):
            if motor["order"] == order:
                move_list.extend([motor["motor"], motor["position"]])
        yield from bps.mv(*move_list)


## TODO: this is an example of a function I would want available in bsui_local, but wouldn't be available on a personal computer
def view_positions(configuration_name):
    ## Prints positions of motors in that configuration without moving anything
    configuration_setpoints = GLOBAL_CONFIGURATION_DICT[configuration_name]
    for indexMotor, motor in enumerate(configuration_setpoints):
        print(motor["motor"].read())


position_RSoXSDiagnosticModule_OutOfBeamPath = 145
position_RSoXSSlitAperture_FullyOpen = 10
position_BeamstopWAXS_InBeamPath = 69.6  ## Out is 3
position_CameraWAXS_InBeamPath = 2
position_CameraWAXS_OutOfBeamPath = -94

## TODO: split into 2 dictionaries.  One that users can use and I can make a list of names to use in spreadsheet sanitization and then one dictionary that is used for one-time setup.
default_configurations = {
    "NoBeam": [
        {"motor": slits1.vsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits1.hsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits2.vsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits2.hsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits3.vsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits3.hsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": shutter_y, "position": 44, "order": 1},
        {"motor": izero_y, "position": 144, "order": 1},
        {"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
        {"motor": BeamStopW, "position": 3, "order": 1},
        {"motor": BeamStopS, "position": 3, "order": 1},
        #{"motor": sam_Y, "position": 345, "order": 1},  ## TODO: Might need to remove if issue with gate valve closed.  maybe make separate configuration, solid_sample_out
        #{"motor": sam_X, "position": 0, "order": 1},
        #{"motor": sam_Z, "position": 0, "order": 1},
        #{"motor": sam_Th, "position": 0, "order": 1},
        {"motor": TEMZ, "position": 1, "order": 1},
    ],
    "MirrorConfiguration_RSoXS": [
        {"motor": mir1.x, "position": 1.3, "order": 0},
        {"motor": mir1.y, "position": -18, "order": 1},
        {"motor": mir1.z, "position": 0, "order": 2},
        {"motor": mir1.pitch, "position": 0.57, "order": 3},
        {"motor": mir1.roll, "position": 0, "order": 4},
        {"motor": mir1.yaw, "position": 0, "order": 5},
        {"motor": mir3.x, "position": 24.2, "order": 0},
        {"motor": mir3.y, "position": 18, "order": 1},
        {"motor": mir3.z, "position": 0, "order": 2},
        {"motor": mir3.pitch, "position": 7.8, "order": 3},
        {"motor": mir3.roll, "position": 0, "order": 4},
        {"motor": mir3.yaw, "position": 0, "order": 5},
    ],
    "WAXS_OpenBeamImages": [
        {"motor": en, "position": 150, "order": 0},
        {"motor": slitsc, "position": -0.01, "order": 0},
        {"motor": izero_y, "position": position_RSoXSDiagnosticModule_OutOfBeamPath, "order": 0},
        {
            "motor": shutter_y,
            "position": 2.2,
            "order": 0,
        },  # {"motor": shutter_y, "position": 25, "order": 0}, #{"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": position_RSoXSSlitAperture_FullyOpen, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
    ],
    "WAXSNEXAFS": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.21, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 0.4, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 1, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 1, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
    "WAXSNEXAFS_LowFlux": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.21, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 0.4, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 1, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 1, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -1.05, "order": 2},  # -0.05
    ],
    "WAXS": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.21, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 0.4, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 1, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 1, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
    "WAXS_LowFlux": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.21, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 0.4, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 1, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 1, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -1.05, "order": 2},
    ],
    "WAXSNEXAFS_Liquids": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.1, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.7, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.75, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 1.5, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 5, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 5, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
    "WAXS_Liquids": [
        {"motor": TEMZ, "position": 1, "order": 0},
        {"motor": slits1.vsize, "position": 0.1, "order": 0},
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hsize, "position": 0.7, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vsize, "position": 0.75, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hsize, "position": 1.5, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vsize, "position": 5, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hsize, "position": 5, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
        {"motor": shutter_y, "position": 2.2, "order": 0},
        {"motor": izero_y, "position": -31, "order": 0},
        {"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
}

GLOBAL_CONFIGURATION_DICT.update(default_configurations)


def add_configuration(configuration_name, configuration_setpoints):
    GLOBAL_CONFIGURATION_DICT.update({configuration_name: configuration_setpoints})


def remove_configuration(configuration_name):
    GLOBAL_CONFIGURATION_DICT.pop(configuration_name, None)


## TODO: break up the function so that undulator movements are separated.  We lose PV write access during maintenance/shutdown periods.
def all_out():
    yield from psh10.close()
    yield from load_configuration("NoBeam")
    yield from bps.mv(
        slitsc,
        -0.05,
    )
    print("moving back to 1200 l/mm grating")
    yield from grating_to_1200()
    print("resetting cff to 2.0")
    yield from bps.mv(mono_en.cff, 2)
    print("moving to 270 eV")
    yield from bps.mv(en, 270)
    yield from bps.mv(en.polarization, 0)
    bl.md.update(
        {
            "RSoXS_Config": "inactive",
            "RSoXS_Main_DET": None,
            "RSoXS_WAXS_SDD": None,
            "RSoXS_WAXS_BCX": None,
            "RSoXS_WAXS_BCY": None,
            "RSoXS_SAXS_SDD": None,
            "RSoXS_SAXS_BCX": None,
            "RSoXS_SAXS_BCY": None,
        }
    )
    print("All done - Happy NEXAFSing")
