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
from nbs_bl.hw import (
    ring_current,
    fesh, 
    psh4,
    sst_control,
    gvll, 
    gv27a,
    sam_X,
    waxs_det,
    mc19_fault, 
    mc20_fault, 
    mc21_fault,
    rsoxs_pg_main_val, 
    rsoxs_ccg_main_val
)
from ..HW.detectors import (
    start_det_cooling,
    stop_det_cooling,
    dark_frame_preprocessor_waxs_spirals,
    dark_frame_preprocessor_waxs,
    # dark_frame_preprocessor_saxs,
)

RE = bl.run_engine


run_report(__file__)


def waxs_back_on():
   
   waxs_det = bl["waxs_det"]
   
   yield from bps.mv(
       waxs_det.cam.temperature, -80, waxs_det.cam.enable_cooling, 1, waxs_det.cam.bin_x, 4, waxs_det.cam.bin_y, 4
   )


# def saxs_back_on():
    # yield from bps.mv(
        # saxs_det.cam.temperature, -80, saxs_det.cam.enable_cooling, 1, saxs_det.cam.bin_x, 4, saxs_det.cam.bin_y, 4
    # )


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



suspend_current = SuspendFloor(
    ring_current.target,
    resume_thresh=350,
    suspend_thresh=250,
    sleep=30,
    tripped_message="Beam Current is below threshold, will resume when above 350 mA",
    pre_plan=beamdown_notice,
    post_plan=beamup_notice,
)


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


# suspend_saxs_temp_low = SuspendFloor(
    # saxs_det.cam.temperature_actual,
    # resume_thresh=-85,
    # suspend_thresh=-90,
    # sleep=30,
    # tripped_message="the detector temperature is below -90C, will resume when above -85C\n this likely means the detector has died and needs to be restarted",
    # pre_plan=det_down_notice,
    # post_plan=saxs_back_on,
# )


# suspend_saxs_temp_high = SuspendCeil(
    # saxs_det.cam.temperature_actual,
    # resume_thresh=-78,
    # suspend_thresh=-75,
    # sleep=30,
    # tripped_message="the detector temperature is above -75C, will resume when below -78C",
    # pre_plan=det_down_notice,
    # post_plan=temp_ok_notice,
# )


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


# if there is no scatter, pause


logger = logging.getLogger("bluesky")
mail_handler = OSEmailHandler()
mail_handler.setLevel("ERROR")  # Only email for if the level is ERROR or higher (CRITICAL).

safe_handler = MakeSafeHandler()
safe_handler.setLevel("ERROR")  # is this correct?


def turn_on_checks():
    RE.install_suspender(suspend_shutter1)
    RE.install_suspender(suspend_current)
    #RE.install_suspender(suspend_pressure)
    RE.install_suspender(suspend_pressure2)
    RE.install_suspender(suspend_gate_valve)
    RE.install_suspender(suspendmc19_amp_fault)
    RE.install_suspender(suspendmc20_amp_fault)
    RE.install_suspender(suspendmc21_amp_fault)
    #RE.install_suspender(suspend_waxs_temp_low)
    #RE.install_suspender(suspend_waxs_temp_high)
    # RE.install_suspender(suspend_saxs_temp_low)
    # RE.install_suspender(suspend_saxs_temp_high)
    RE.install_suspender(suspendx)
    RE.install_suspender(suspend_control)
    logger.addHandler(safe_handler)
    logger.addHandler(mail_handler)


def turn_off_checks():
    RE.remove_suspender(suspend_shutter1)
    RE.remove_suspender(suspend_gate_valve)
    RE.remove_suspender(suspend_pressure2)
    RE.remove_suspender(suspend_current)
    RE.remove_suspender(suspendx)
    RE.remove_suspender(suspendmc19_amp_fault)
    RE.remove_suspender(suspendmc20_amp_fault)
    RE.remove_suspender(suspendmc21_amp_fault)
    #RE.remove_suspender(suspend_pressure)
    #RE.remove_suspender(suspend_waxs_temp_low)
    #RE.remove_suspender(suspend_waxs_temp_high)
    # RE.remove_suspender(suspend_saxs_temp_low)
    # RE.remove_suspender(suspend_saxs_temp_high)
    RE.remove_suspender(suspendx)
    RE.remove_suspender(suspend_control)
    logger.removeHandler(safe_handler)
    logger.removeHandler(mail_handler)


def waxs_spiral_mode():
   try:
       RE.preprocessors.remove(dark_frame_preprocessor_waxs_spirals)
   except ValueError:
       pass
   try:
       RE.preprocessors.remove(dark_frame_preprocessor_waxs)
   except ValueError:
       pass
   RE.preprocessors.append(dark_frame_preprocessor_waxs_spirals)


def waxs_normal_mode():
   try:
       RE.preprocessors.remove(dark_frame_preprocessor_waxs_spirals)
   except ValueError:
       pass
   try:
       RE.preprocessors.remove(dark_frame_preprocessor_waxs)
   except ValueError:
       pass
   RE.preprocessors.append(dark_frame_preprocessor_waxs)


# install preprocessors
waxs_normal_mode()

# RE.preprocessors.append(dark_frame_preprocessor_saxs)
# install handlers for errors and install suspenders
turn_on_checks()
