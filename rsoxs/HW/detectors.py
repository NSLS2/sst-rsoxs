import bluesky.plan_stubs as bps
from rsoxs.plans.plan_stubs import skinnystage, skinnyunstage
import bluesky.plans as bp
from bluesky.preprocessors import make_decorator
import bluesky_darkframes

from nbs_bl.hw import (
    en, 
    shutter_control, 
    shutter_open_time, 
    #Det_S, 
    Det_W, 
    sam_Th, 
    sam_X, 
    sam_Y, 
    waxs_det,
)
from nbs_bl.plans.scans import nbs_count
from nbs_bl.printing import boxed_text, run_report
from ..HW.signals import default_sigs
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl

run_report(__file__)


# saxs_det = RSOXSGreatEyesDetector('XF:07ID1-ES:1{GE:1}', name='Small Angle CCD Detector',
#                                   read_attrs=['tiff', 'stats1.total', 'saturated','under_exposed','cam']
#                                   )

# saxs_det.cam.read_attrs = ['acquire_time']
# saxs_det.transform_type = 3
# saxs_det.cam.ensure_nonblocking()
# saxs_det.setup_cam()
# #
"""
waxs_det = RSOXSGreatEyesDetector(
   "XF:07ID1-ES:1{GE:2}",
   name="Wide Angle CCD Detector",
   read_attrs=['tiff', 'stats1.total', 'saturated','under_exposed','cam'],
)

waxs_det.cam.read_attrs = ["acquire_time"]
waxs_det.transform_type = 1
waxs_det.cam.ensure_nonblocking()
waxs_det.setup_cam()

# saxs_det.stats1.name = "SAXS fullframe"
waxs_det.stats1.name = "WAXS fullframe"
"""

# to simulate, use this line, and comment out the relevent detector above
# saxs_det = SimGreatEyes(name="Simulated SAXS camera")

## TODO: the stop_det_cooling, start_det_cooling, set_exposure, and exposure functions probably can be removed, as they are in devices/detectors.py in the RSoXSGreatEyesDetector class.
## Once the camera is fully working, try commenting these out and testing.

def stop_det_cooling():
    # yield from saxs_det.cooling_off()
    waxs_det = bl["waxs_det"]
    yield from waxs_det.cooling_off_plan()


def start_det_cooling():
    # yield from saxs_det.set_temp(-80)
    waxs_det = bl["waxs_det"]
    yield from waxs_det.set_temp_plan(-80)


def set_exposure(exposure):
    waxs_det = bl["waxs_det"]

    if exposure > 0.001 and exposure < 1000:
        # saxs_det.set_exptime(exposure)
        waxs_det.set_exptime(exposure)
        shutter_open_time.set(exposure * 1000).wait()
        for sig in default_sigs:
            if hasattr(sig, "exposure_time"):
                sig.exposure_time.set(max(0.3, exposure - 0.5)).wait()
    else:
        print("Invalid time, exposure time not set")


def exposure():
    waxs_det = bl["waxs_det"]
    return "   " + waxs_det.exposure()  # + "\n   " + waxs_det.exposure()


def snapshot(secs=0, count=1, name=None, energy=None, detn="waxs", n_exp=1):
    """
    Takes one or more images.
    Also useful to clear out any charge accumulated in the detector.
    
    In the past: needed before starting scans or snapping images
    TODO: find out if the above is still relevant.  Doesn't seem so.
    
    
    TODO: remove name and energy after verifying that they are not used elsewhere.  They are not used in snapwaxs.
    
    """
    waxs_det = bl["waxs_det"]

    cameras_lookup = {"waxs": waxs_det} ## Used to have SAXS camera as well
    camera = cameras_lookup[detn]
   
    if count <= 1: count = 1 ## Should take at least one image
    else: count = round(count) ## count should be int

    if isinstance(energy, float):
        yield from bps.mv(en, energy)

    boxed_text(
        "Snapshot",
        "Taking {} snapshot(s) of {} second(s) with {}".format(
            count, secs, camera.name
        ),
        "red",
    )
    
    yield from nbs_count(
                         num = count,
                         use_2d_detector = True,
                         dwell = secs,
                         n_exposures = n_exp,
    )


# adding for testing

count = bp.count


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
    ## TODO: confirm if the below line is what is capturing the dark image
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


# dark_frame_preprocessor_saxs = bluesky_darkframes.DarkFramePreprocessor(
#     dark_plan=dark_plan,
#     detector=saxs_det,
#     max_age=300,
#     locked_signals=[
#         saxs_det.cam.acquire_time,
#         Det_S.user_setpoint,
#         saxs_det.cam.bin_x,
#         saxs_det.cam.bin_y,
#     ],
#     limit=20,
# )


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


## TODO: It doesn't seem like this is used elsewhere in the code, so test, delete, and/or consolidate more meaningfully elsewhere.
dark_frames_enable_waxs = make_decorator(dark_frame_preprocessor_waxs)()
# dark_frames_enable_saxs = make_decorator(dark_frame_preprocessor_saxs)()


