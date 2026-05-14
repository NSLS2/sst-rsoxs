import bluesky.plan_stubs as bps

from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.hw import (
    en, 
)
from nbs_bl.plans.scans import nbs_count
from nbs_bl.printing import boxed_text, run_report


run_report(__file__)


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

