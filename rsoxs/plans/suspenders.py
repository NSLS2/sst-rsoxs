import logging
import bluesky.plan_stubs as bps
from bluesky.suspenders import SuspendBoolHigh, SuspendFloor, SuspendCeil, SuspendBoolLow, SuspendWhenChanged
from nbs_bl.printing import run_report
from ..Functions.contingencies import (
    beamdown_notice,
    beamup_notice,
    enc_clr_gx,
    enc_clr_x,
    OSEmailHandler,
    MakeSafeHandler,
    det_down_notice,
    temp_bad_notice,
    temp_ok_notice,
    amp_fault_clear_19,
    amp_fault_clear_20,
    amp_fault_clear_21,
)


from nbs_bl.beamline import GLOBAL_BEAMLINE as bl

from ..HW.detectors import (
    start_det_cooling,
    stop_det_cooling,
    dark_frame_preprocessor_waxs_spirals,
    dark_frame_preprocessor_waxs,
    # dark_frame_preprocessor_saxs,
)

RE = bl.run_engine

suspender_selection = {"waxs": True, "shutter": True, "general": True, "motor": True}

def turn_on_checks():
    for key in suspender_selection:
        suspender_selection[key] = True

def turn_off_checks():
    for key in suspender_selection:
        suspender_selection[key] = False

def waxs_back_on():
   
   waxs_det = bl["waxs_det"]
   
   yield from bps.mv(
       waxs_det.cam.temperature, -80, waxs_det.cam.enable_cooling, 1, waxs_det.cam.bin_x, 4, waxs_det.cam.bin_y, 4
   )


def create_waxs_suspenders():
    waxs_det = bl["waxs_det"]
    suspend_waxs_temp_low = SuspendFloor(
        waxs_det.cam.temperature_actual,
        resume_thresh=-85,
        suspend_thresh=-90,
        sleep=30,
        tripped_message="the detector temperature is below -90C, will resume when above -85C\n this likely means the detector has died and needs to be restarted",
        pre_plan=det_down_notice,
        post_plan=waxs_back_on,
    )

    suspend_waxs_temp_high = SuspendCeil(
        waxs_det.cam.temperature_actual,
        resume_thresh=-78,
        suspend_thresh=-75,
        sleep=30,
        tripped_message="the detector temperature is above -75C, will resume when below -78C",
        pre_plan=temp_bad_notice,
        post_plan=temp_ok_notice,
    )

    return [suspend_waxs_temp_low, suspend_waxs_temp_high]

def create_shutter_suspenders():
    gvll = bl["gvll"]
    psh4 = bl["psh4"]
    fesh = bl["fesh"]
    gv27a = bl["gv27a"]

    suspend_gvll = SuspendBoolLow(
        gvll.state,
        sleep=30,
        tripped_message="Gate valve to load lock is closed, waiting for it to open",
    )

    suspend_shutter4 = SuspendBoolHigh(
        psh4.state,
        sleep=30,
        tripped_message="Shutter 4 Closed, waiting for it to open",
        pre_plan=beamdown_notice,
        post_plan=beamup_notice,
    )

    suspend_shutter1 = SuspendBoolHigh(
        fesh.state,
        sleep=30,
        tripped_message="Front End Shutter Closed, waiting for it to open",
        pre_plan=beamdown_notice,
        post_plan=beamup_notice,
    )

    suspend_gate_valve = SuspendBoolLow(
        gv27a.state,
        sleep=1,
        tripped_message="Gate valve is closed, pressure is probably bad. waiting for it to open.",
        pre_plan=beamdown_notice,
        post_plan=beamup_notice,
    )

    return [suspend_gvll, suspend_shutter4, suspend_shutter1, suspend_gate_valve]

def create_general_suspenders():
    ring_current = bl["ring_current"]
    rsoxs_pg_main_val = bl["rsoxs_pg_main_val"]
    rsoxs_ccg_main_val = bl["rsoxs_ccg_main_val"]
    sst_control = bl["sst_control"]

    suspend_current = SuspendFloor(
        ring_current.target,
        resume_thresh=350,
        suspend_thresh=250,
        sleep=30,
        tripped_message="Beam Current is below threshold, will resume when above 350 mA",
        pre_plan=beamdown_notice,
        post_plan=beamup_notice,
    )

    suspend_pressure = SuspendCeil(
        rsoxs_pg_main_val,
        resume_thresh=0.1,
        suspend_thresh=2,
        sleep=30,
        tripped_message="Pressure in the Chamber is above the threshold for having cooling on",
        pre_plan=stop_det_cooling,
        post_plan=start_det_cooling,
    )


    suspend_pressure2 = SuspendCeil(
        rsoxs_ccg_main_val,
        resume_thresh=5e-7,
        suspend_thresh=1e-6,
        sleep=5,
        tripped_message="Pressure in the Chamber is too high - beamline has probably tripped",
    )

    suspend_control = SuspendWhenChanged(
        sst_control,
        expected_value="RSoXS",
        allow_resume=True,
        sleep=1,
        tripped_message="RSoXS does not currently have control",
    )

    return [suspend_current, suspend_pressure, suspend_pressure2, suspend_control]

def create_motor_suspenders():
    sam_X = bl["sam_X"]
    mc19_fault = bl["mc19_fault"]
    mc20_fault = bl["mc20_fault"]
    mc21_fault = bl["mc21_fault"]

    suspendx = SuspendBoolHigh(
        sam_X.enc_lss,
        sleep=40,
        tripped_message="Sample X has lost encoder position, resetting, please wait, scan will "
        "resume automatically.",
        pre_plan=enc_clr_x,
    )


    suspendmc19_amp_fault = SuspendBoolLow(
        mc19_fault,
        sleep=10,
        tripped_message="Amp fault detected in MC19, waiting for clear before continuing",
        pre_plan=amp_fault_clear_19,
    )


    suspendmc20_amp_fault = SuspendBoolLow(
        mc20_fault,
        sleep=10,
        tripped_message="Amp fault detected in MC20, waiting for clear before continuing",
        pre_plan=amp_fault_clear_20,
    )


    suspendmc21_amp_fault = SuspendBoolLow(
        mc21_fault,
        sleep=10,
        tripped_message="Amp fault detected in MC21, waiting for clear before continuing",
        pre_plan=amp_fault_clear_21,
    )


    suspendgx = SuspendBoolHigh(
        sam_X.enc_lss,
        sleep=40,
        tripped_message="Grating X has lost encoder position, resetting, please wait, scan will "
        "resume automatically.",
        pre_plan=enc_clr_gx,
    )

    return [suspendx, suspendmc19_amp_fault, suspendmc20_amp_fault, suspendmc21_amp_fault, suspendgx]

def get_suspenders():
    suspenders = []
    if suspender_selection["waxs"]:
        suspenders.extend(create_waxs_suspenders())
    if suspender_selection["shutter"]:  
        suspenders.extend(create_shutter_suspenders())
    if suspender_selection["general"]:
        suspenders.extend(create_general_suspenders())
    if suspender_selection["motor"]:
        suspenders.extend(create_motor_suspenders())
    return suspenders