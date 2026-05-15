import bluesky.plan_stubs as bps
import bluesky_darkframes
from bluesky.suspenders import SuspendFloor, SuspendCeil

from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.hw import (
    shutter_control, 
    shutter_open_time, 
    #Det_S, 
    Det_W, 
    sam_Th, 
    sam_X, 
    sam_Y, 
)


from rsoxs.plans.plan_stubs import skinnystage, skinnyunstage
from ..Functions.contingencies import (
    det_down_notice,
    temp_bad_notice,
    temp_ok_notice,
)


RE = bl.run_engine





def dark_plan(det):
    #yield from det.skinnyunstage()
    yield from skinnyunstage(det)

    #det.skinnyunstage()
    # yield from bps.mv(det.cam.shutter_mode, 0)
    ## Saves the number of exposures we would want to take for light images
    n_exp = det.cam.num_images.get()
    ## Sets number of exposures to 1 so that it only takes one dark image regardless of however many repeat light images are taken.
    ## Disables shutter because the shutter needs to be closed to take a dark image.
    yield from bps.mv(det.cam.num_images, 1, det.cam.shutter_mode, 0)
    
    #yield from det.skinnystage()
    yield from skinnystage(det)
    # det.skinnystage()
    det.log.debug("Skinnystaged", det.name)
    yield from bps.trigger(det, group="darkframe-trigger")
    yield from bps.wait("darkframe-trigger")
    snapshot = bluesky_darkframes.SnapshotDevice(det)
    
    #yield from det.skinnyunstage()
    yield from skinnyunstage(det)

    #det.skinnyunstage()
    ## If the shutter is to be used for light images, it is enabled
    if det.useshutter:
        yield from bps.mv(det.cam.shutter_mode, 2)
    ## Desired number of exposures is restored for light images
    yield from bps.mv(det.cam.num_images, n_exp)
    #yield from det.skinnystage()
    yield from skinnystage(det)
    return snapshot





def waxs_back_on():  
   waxs_det = bl["waxs_det"]  
   yield from bps.mv(
       waxs_det.cam.temperature, -80, waxs_det.cam.enable_cooling, 1, waxs_det.cam.bin_x, 4, waxs_det.cam.bin_y, 4
   )



"""
Due to the uninstall/reinstall of the Greateyes WAXS detector 2025-2026 along with other instnaces where the detector is switched off, 
the following try/except code is being implemented to organize detector setup in one place
and minimize the need for ad hoc commenting and uncommenting of code, as was done in the past
(https://github.com/NSLS2/sst-rsoxs/issues/55).

A long-term goal is to use nbs_bl's mode switching functionality
that can handle cases when the detector is switched off.  
However, implementing that functionality currently would cause other errors in the current state of this codebase.

As a short-term workaround, the try/except code below will be used.
"""


try:
    from nbs_bl.hw import waxs_det

    ## TODO: Gather waxs_det-related code from HW.contingencies and HW.detectors
    ## Include suspenders




    ## Darkframe setup ##################################################################################
    ## blueskyproject.io/bluesky-darkframes/reference.html#bluesky_darkframes.DarkFramePreprocessor

    ## max_age
    ## Time (in seconds?) after which a new dark image should be taken regardless of whether any other conditions have changed.

    ## locked_signals
    ## For normal operation, if the motor positions for the locked_signals items change, then a new dark should be taken.
    ## In spirals mode, taking a dark for each sample position would take a lot of extra time, so the sam_X, sam_Th, and sam_Y setpoints are removed.

    dark_frame_preprocessor_waxs = bluesky_darkframes.DarkFramePreprocessor(
        dark_plan=dark_plan,
        detector=waxs_det,
        max_age=180,
        locked_signals=[
            waxs_det.cam.acquire_time,
            Det_W.user_setpoint,
            waxs_det.cam.bin_x,
            waxs_det.cam.bin_y,
            sam_X.user_setpoint,
            sam_Th.user_setpoint,
            sam_Y.user_setpoint,
        ],
        limit=100,
    )
    dark_frame_preprocessor_waxs_spirals = bluesky_darkframes.DarkFramePreprocessor(

        dark_plan=dark_plan,
        detector=waxs_det,
        max_age=120,
        locked_signals=[
            waxs_det.cam.acquire_time,
            Det_W.user_setpoint,
            waxs_det.cam.bin_x,
            waxs_det.cam.bin_y,
        ],
        limit=10,
    )

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





    ## Suspenders ##################################################################################
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






except ImportError as error:
    print("waxs_det was not imported.  This may be because the detector is switched off.  Downstream code that relies on waxs_det will not run.")

except Exception as error:
    ## TODO: elaborate here later.  Meant to catch instances where the import worked but other setup did not.
    print("Some other error.")