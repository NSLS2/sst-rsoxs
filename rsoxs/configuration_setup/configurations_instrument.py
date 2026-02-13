import numpy as np
import copy

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
    #Det_W,
    # Det_S,
    #BeamStopS,
    BeamStopW,
    sam_Th,
    sam_Z,
    sam_Y,
    sam_X,
    TEMY,
    TEMZ,
    #mir4OLD,
    dm7_y,
)

from ..HW.energy import mono_en, grating_to_1200

GLOBAL_CONFIGURATION_DICT = GLOBAL_USER_STATUS.request_status_dict("RSoXS_Config")


def load_configuration(
        configuration_name,
        dryrun = False,
):
    print("Loading instrument configuration: " + str(configuration_name))

    if dryrun == True: return

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
            "RSoXS_WAXS_SDD": 31.960803248151926,
            "RSoXS_WAXS_BCX": 474,
            "RSoXS_WAXS_BCY": 502,
            "WAXS_Mask": [(477.418, 535.415), (446.074, 511.344), (872.214, -0.476), (948.916, -0.476)],
            "RSD": None,
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
position_BeamstopWAXS_InBeamPath = 20 #69.6 from May 2025 to December 2025  ## Out is 3
position_CameraWAXS_InBeamPath = 2
position_CameraWAXS_OutOfBeamPath = -94

## TODO: split into 2 dictionaries.  One that users can use and I can make a list of names to use in spreadsheet sanitization and then one dictionary that is used for one-time setup.
default_configurations = {
    "Mirrors": [
        {"motor": mir1.x, "position": 1.3, "order": 0},
        {"motor": mir1.y, "position": -18, "order": 1},
        {"motor": mir1.z, "position": 0, "order": 2},
        {"motor": mir1.pitch, "position": 0.57, "order": 3},
        {"motor": mir1.roll, "position": 0, "order": 4},
        {"motor": mir1.yaw, "position": 0, "order": 5},
        {"motor": mir3.x, "position": 24.2, "order": 0},
        {"motor": mir3.y, "position": 18, "order": 1},
        {"motor": mir3.z, "position": 0, "order": 2},
        {"motor": mir3.pitch, "position": 7.84, "order": 3},
        {"motor": mir3.roll, "position": 0, "order": 4},
        {"motor": mir3.yaw, "position": 0, "order": 5},
    ],
    ## TODO: include FOE slits here and try again to include front-end slits

    "SlitC_Retracted": [
        {"motor": slitsc, "position": -3.05, "order": 0},
    ],
    "SlitC_NEXAFS": [
        {"motor": slitsc, "position": -0.05, "order": 0},
    ],

    "DMRSoXS_Retracted": [
        {"motor": izero_y, "position": 144, "order": 0},
    ],
    "DMRSoXS_Mesh": [
        {"motor": izero_y, "position": -31, "order": 0},
    ],
    "DMRSoXS_FluorescenceScreen": [
        {"motor": izero_y, "position": 2, "order": 0},
    ],
    "DMRSoXS_Photodiode": [
        {"motor": izero_y, "position": 35, "order": 0},
    ],

    "FastShutter_Retracted": [
        {"motor": shutter_y, "position": 44, "order": 0},
    ],
    "FastShutter": [
        {"motor": shutter_y, "position": 2.2, "order": 0},
    ],

    "RSoXSSlits_Retracted": [
        {"motor": slits1.vsize, "position": 10, "order": 0},
        {"motor": slits1.hsize, "position": 10, "order": 0},
        {"motor": slits2.vsize, "position": 10, "order": 0},
        {"motor": slits2.hsize, "position": 10, "order": 0},
        {"motor": slits3.vsize, "position": 10, "order": 0},
        {"motor": slits3.hsize, "position": 10, "order": 0},
    ],
    "RSoXSSlits_Centers": [
        {"motor": slits1.vcenter, "position": -0.55, "order": 0},
        {"motor": slits1.hcenter, "position": -0.18, "order": 0},
        {"motor": slits2.vcenter, "position": -0.873, "order": 0},
        {"motor": slits2.hcenter, "position": -0.1, "order": 0},
        {"motor": slits3.vcenter, "position": -0.45, "order": 0},
        {"motor": slits3.hcenter, "position": 0.2, "order": 0},
    ],
    ## Normally, when I have 2D detectors and am running mixed scattering and NEXAFS measurements, I want all 3 sets of slits to be set for scattering and have same slit configurations across RSoXS and NEXAFS.
    ## However, when there is no 2D detector, only slit 1 matters
    "RSoXSSlits_ApertureSizes_SolidSamples": [
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits2.vsize, "position": 10, "order": 0},
        {"motor": slits2.hsize, "position": 10, "order": 0},
        {"motor": slits3.vsize, "position": 10, "order": 0},
        {"motor": slits3.hsize, "position": 10, "order": 0},
    ],
    "RSoXSSlits_ApertureSizes_LiquidSamples": [
        {"motor": slits1.vsize, "position": 0.1, "order": 0},
        {"motor": slits1.hsize, "position": 0.12, "order": 0},
        {"motor": slits2.vsize, "position": 10, "order": 0},
        {"motor": slits2.hsize, "position": 10, "order": 0},
        {"motor": slits3.vsize, "position": 10, "order": 0},
        {"motor": slits3.hsize, "position": 10, "order": 0},
    ],
    "RSoXSSlits_ApertureSizes_LiquidSamples_Summer2024": [
        {"motor": slits1.vsize, "position": 0.1, "order": 0},
        {"motor": slits1.hsize, "position": 0.7, "order": 0},
        {"motor": slits2.vsize, "position": 10, "order": 0},
        {"motor": slits2.hsize, "position": 10, "order": 0},
        {"motor": slits3.vsize, "position": 10, "order": 0},
        {"motor": slits3.hsize, "position": 10, "order": 0},
    ],
    "RSoXSSlits_ApertureSizes_LiquidSamples_December2024": [
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.hsize, "position": 0.2, "order": 0},
        {"motor": slits2.vsize, "position": 10, "order": 0},
        {"motor": slits2.hsize, "position": 10, "order": 0},
        {"motor": slits3.vsize, "position": 10, "order": 0},
        {"motor": slits3.hsize, "position": 10, "order": 0},
    ],
    ## For when I have 2D detector and want to reduce slit 1 scattering.
    ## FYI, do not "comment" out dictionary items with triple quotes.  It causes the next element to go missing.
    "RSoXSSlits_ApertureSizes_SolidSamples_20260207": [
        {"motor": slits1.vsize, "position": 0.02, "order": 0},
        {"motor": slits1.hsize, "position": 0.04, "order": 0},
        {"motor": slits2.vsize, "position": 0.21, "order": 0},
        {"motor": slits2.hsize, "position": 0.4, "order": 0},
        {"motor": slits3.vsize, "position": 1, "order": 0},
        {"motor": slits3.hsize, "position": 1, "order": 0},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
    "RSoXSSlits_ApertureSizes_LiquidSamples_20260207": [
        {"motor": slits1.vsize, "position": 0.1, "order": 0},
        {"motor": slits1.hsize, "position": 0.7, "order": 0},
        {"motor": slits2.vsize, "position": 0.75, "order": 0},
        {"motor": slits2.hsize, "position": 1.5, "order": 0},
        {"motor": slits3.vsize, "position": 5, "order": 0},
        {"motor": slits3.hsize, "position": 5, "order": 0},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],

    "SolidSamples_Retracted": [
        {"motor": sam_Y, "position": 345, "order": 0},  ## TODO: Might need to remove if issue with gate valve closed.  maybe make separate configuration, solid_sample_out
        {"motor": sam_X, "position": 0, "order": 0},
        {"motor": sam_Z, "position": 0, "order": 0},
        {"motor": sam_Th, "position": 0, "order": 0},
    ],

    "TEMSample_Retracted": [
        {"motor": TEMZ, "position": 1, "order": 0},
    ],
    "TEMSample": [
        {"motor": TEMZ, "position": 139.7, "order": 0},
        {"motor": TEMY, "position": 0.66, "order": 0},
    ],

    "WAXS_Retracted": [
        {"motor": BeamStopW, "position": 20, "order": 0}, #{"motor": BeamStopW, "position": 3, "order": 0},
        #{"motor": Det_W, "position": -94, "order": 0},
    ],
    "WAXS_Beamstop": [
        {"motor": BeamStopW, "position": 20, "order": 0}, #{"motor": BeamStopW, "position": 69.6, "order": 0},
    ],
    "WAXS_2D": [
        #{"motor": Det_W, "position": 2, "order": 0},
    ],

    "SAXS_Retracted": [
        #{"motor": BeamStopS, "position": 3, "order": 0},
        #{"motor": Det_S, "position": -100, "order": 0},
    ],
    "SAXS_Beamstop": [
        #{"motor": BeamStopS, "position": 20, "order": 0},
    ],
    "SAXS_2D": [
        #{"motor": Det_S, "position": -15, "order": 0},
    ],

    ## TODO: Add PSH7 positions
    ## TODO: Add M4 positions

    "DM7_Retracted": [
        {"motor": dm7_y, "position": 30, "order": 0}, ## Found in this state on 20260129
    ],
    "DM7_Photodiode": [
        {"motor": dm7_y, "position": -12.25, "order": 0}, 
    ],
    "DM7_FS13": [
        {"motor": dm7_y, "position": -42, "order": 0}, 
    ],
    
    ## TODO: delete configurations from here onwards if the ones below work.
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
        #{"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_OutOfBeamPath, "order": 1},
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
        #{"motor": Det_W, "position": position_CameraWAXS_InBeamPath, "order": 1},
        {"motor": BeamStopW, "position": position_BeamstopWAXS_InBeamPath, "order": 1},
        {"motor": slitsc, "position": -3.05, "order": 2},
    ],
}



## Construct configurations that combine the components above.
## Can't just copy.deepcopy configurations to piece together new configurations because the motor objects might contain references back to themselves, and then we get `RecursionError: maximum recursion depth exceeded` when we try to load `profile_collection`
## Instead, make a new ditionary
default_configurations["NoBeam"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["RSoXSSlits_Retracted"]
]
## Not sure if this is necessary.  Had made it to run count scans when I don't have beam to test automated workflow.

## TODO: maybe have a Detectors_Retracted_Science and Detectors_Retracted_Commissioning version where the latter includes upstream fluorescence screens like FS1, FS6, and FS7?  Unsure how to treat I0 because I do treat it as a detector for commissioning purposes.
default_configurations["Detectors_Retracted"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["WAXS_Retracted"] ## Protect detectors first
]
"""
default_configurations["Detectors_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["SAXS_Retracted"]
    )
"""
default_configurations["Detectors_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["DM7_Retracted"]
    )


default_configurations["RSoXS_Retracted"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["Detectors_Retracted"] ## Protect detectors first
]
default_configurations["RSoXS_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["SolidSamples_Retracted"] ## Protect samples next
    )
default_configurations["RSoXS_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["TEMSample_Retracted"]
    )
default_configurations["RSoXS_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 2)}
    for item in default_configurations["RSoXSSlits_Retracted"]
    )
default_configurations["RSoXS_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 2)}
    for item in default_configurations["FastShutter_Retracted"]
    )
default_configurations["RSoXS_Retracted"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 2)}
    for item in default_configurations["DMRSoXS_Retracted"]
    )


#default_configurations["NEXAFSStation"]
## TODO: Do things like putting M4 into place, setting energy to 270 eV, polarization to 0.

default_configurations["RSoXS_Upstream"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["SlitC_Retracted"]
]
default_configurations["RSoXS_Upstream"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_Centers"]
    )
default_configurations["RSoXS_Upstream"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_ApertureSizes_SolidSamples"]
    )
default_configurations["RSoXS_Upstream"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["DMRSoXS_Mesh"]
    )
default_configurations["RSoXS_Upstream"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["FastShutter"]
    )

default_configurations["RSoXS_Upstream_Liquids"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["SlitC_Retracted"]
]
default_configurations["RSoXS_Upstream_Liquids"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_Centers"]
    )
default_configurations["RSoXS_Upstream_Liquids"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_ApertureSizes_LiquidSamples"]
    )
default_configurations["RSoXS_Upstream_Liquids"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["DMRSoXS_Mesh"]
    )
default_configurations["RSoXS_Upstream_Liquids"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["FastShutter"]
    )

default_configurations["DM7NEXAFS"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["RSoXS_Upstream"]
]
default_configurations["DM7NEXAFS"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["Detectors_Retracted"]
    )
## Start with all detectors retracted and then bring in the desired detectors
devices_to_update = {item["motor"]: item for item in default_configurations["DM7_Photodiode"]}
for item in default_configurations["DM7NEXAFS"]:
    if item["motor"] in devices_to_update:
        item.update(devices_to_update[item["motor"]])


configuration_name = "DM7_FluorescenceImage"
configurations_to_combine = [
    "RSoXS_Upstream",
    "Detectors_Retracted"
]
configurations_to_overwrite = [
    "DM7_FS13",
]
default_configurations[configuration_name] = []
## First build base configuration where all detectors are retracted
for configuration_to_combine in configurations_to_combine:
    default_configurations[configuration_name].extend(
        {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
        for item in default_configurations[configuration_to_combine]
        )
## Then bring in the desired detectors
for configuration_to_overwrite in configurations_to_overwrite:
    devices_to_update = {item["motor"]: item for item in default_configurations[configuration_to_overwrite]}
    for item in default_configurations[configuration_name]:
        if item["motor"] in devices_to_update:
            item.update(devices_to_update[item["motor"]])


default_configurations["DM7NEXAFS_Liquids"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["RSoXS_Upstream_Liquids"]
]
default_configurations["DM7NEXAFS_Liquids"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["Detectors_Retracted"]
    )
## Start with all detectors retracted and then bring in the desired detectors
devices_to_update = {item["motor"]: item for item in default_configurations["DM7_Photodiode"]}
for item in default_configurations["DM7NEXAFS_Liquids"]:
    if item["motor"] in devices_to_update:
        item.update(devices_to_update[item["motor"]])










default_configurations["RSoXS_Upstream_Liquids_Summer2024"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["SlitC_Retracted"]
]
default_configurations["RSoXS_Upstream_Liquids_Summer2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_Centers"]
    )
default_configurations["RSoXS_Upstream_Liquids_Summer2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_ApertureSizes_LiquidSamples_Summer2024"]
    )
default_configurations["RSoXS_Upstream_Liquids_Summer2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["DMRSoXS_Mesh"]
    )
default_configurations["RSoXS_Upstream_Liquids_Summer2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["FastShutter"]
    )

default_configurations["DM7NEXAFS_Liquids_Summer2024"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["RSoXS_Upstream_Liquids_Summer2024"]
]
default_configurations["DM7NEXAFS_Liquids_Summer2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["Detectors_Retracted"]
    )
## Start with all detectors retracted and then bring in the desired detectors
devices_to_update = {item["motor"]: item for item in default_configurations["DM7_Photodiode"]}
for item in default_configurations["DM7NEXAFS_Liquids_Summer2024"]:
    if item["motor"] in devices_to_update:
        item.update(devices_to_update[item["motor"]])





default_configurations["RSoXS_Upstream_Liquids_December2024"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["SlitC_Retracted"]
]
default_configurations["RSoXS_Upstream_Liquids_December2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_Centers"]
    )
default_configurations["RSoXS_Upstream_Liquids_December2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"])}
    for item in default_configurations["RSoXSSlits_ApertureSizes_LiquidSamples_December2024"]
    )
default_configurations["RSoXS_Upstream_Liquids_December2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["DMRSoXS_Mesh"]
    )
default_configurations["RSoXS_Upstream_Liquids_December2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["FastShutter"]
    )

default_configurations["DM7NEXAFS_Liquids_December2024"] = [
    {"motor": item["motor"], "position": item["position"], "order": item["order"]}
    for item in default_configurations["RSoXS_Upstream_Liquids_December2024"]
]
default_configurations["DM7NEXAFS_Liquids_December2024"].extend(
    {"motor": item["motor"], "position": item["position"], "order": int(item["order"] + 1)}
    for item in default_configurations["Detectors_Retracted"]
    )
## Start with all detectors retracted and then bring in the desired detectors
devices_to_update = {item["motor"]: item for item in default_configurations["DM7_Photodiode"]}
for item in default_configurations["DM7NEXAFS_Liquids_December2024"]:
    if item["motor"] in devices_to_update:
        item.update(devices_to_update[item["motor"]])


GLOBAL_CONFIGURATION_DICT.update(default_configurations)


def add_configuration(configuration_name, configuration_setpoints):
    GLOBAL_CONFIGURATION_DICT.update({configuration_name: configuration_setpoints})


def remove_configuration(configuration_name):
    GLOBAL_CONFIGURATION_DICT.pop(configuration_name, None)


## TODO: break up the function so that undulator movements are separated.  We lose PV write access during maintenance/shutdown periods.
def clear_rsoxs():
    yield from psh10.close()

    ## Move RSoXS out of the way
    yield from load_configuration("RSoXS_Retracted")
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

    ## Move other beamline components to NEXAFS defaults
    yield from bps.mv(
        slitsc,
        -0.05,
    )
    ## The following may lose PV write access during maintenance period
    try:
        print("moving back to 1200 l/mm grating")
        yield from grating_to_1200() ## Involves moving energy, which may lose PV write access
        print("resetting cff to 2.0")
        yield from bps.mv(mono_en.cff, 2)
        print("moving to 270 eV")
        yield from bps.mv(en, 270)
        yield from bps.mv(en.polarization, 0)
    except:
        print("Unable to move EPU at this time.")
    
    print("All done - Happy NEXAFSing")
