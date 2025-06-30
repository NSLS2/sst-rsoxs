import bluesky.plan_stubs as bps
from .fly_alignment import rsoxs_fly_max
from nbs_bl.hw import (
    shutter_control,
    shutter_enable,
    shutter_y,
    sam_X,
    sam_Y,
    sam_Th,
    sam_Z,
    beamstop_waxs,
)
from rsoxs.configuration_setup.configurations_instrument import load_configuration
from ..Functions.alignment import (
    rsoxs_config, 
    correct_bar
    )


## For now, mostly pasting Eliot's fly_find-fiducials, but updating the fly_max function that is used for testing purposes
def find_fiducials(f2=[3.5, -1, -2.4, 1.5], f1=[2.0, -0.9, -1.5, 0.8], y1=-187.5, y2=2):
    thoffset = 0
    angles = [-90 + thoffset, 0 + thoffset, 90 + thoffset, 180 + thoffset]
    xrange = 3.5
    startxss = [f2, f1]
    yield from bps.mv(shutter_enable, 0)
    yield from bps.mv(shutter_control, 0)
    yield from load_configuration("WAXSNEXAFS") ## Don't want to harm camera while rotating sample bar
    beamstop_waxs.kind = "hinted"
    # bec.enable_plots()
    startys = [y2, y1]  # af2 first because it is a safer location
    maxlocs = []
    for startxs, starty in zip(startxss, startys):
        yield from bps.mv(sam_Y, starty, sam_X, startxs[1], sam_Th, 0, sam_Z, 0)
        peaklist = []
        yield from rsoxs_fly_max(
            [beamstop_waxs],
            sam_Y,
            starty - 1,
            starty + 1,
            velocities=[0.2],
            period = 0.5, ## Gives similar point density as Eliot's old fiducial scans.
            open_shutter=True,
            peaklist=peaklist,
            stream=False,
        )
        maxlocs.append(peaklist[-1]["WAXS Beamstop"][sam_Y.name])
        yield from bps.mv(sam_Y, peaklist[-1]["WAXS Beamstop"][sam_Y.name])
        for startx, angle in zip(startxs, angles):
            yield from bps.mv(sam_X, startx, sam_Th, angle)
            yield from bps.mv(shutter_control, 1)
            peaklist = []
            yield from rsoxs_fly_max(
                [beamstop_waxs],
                sam_X,
                startx - 0.5 * xrange,
                startx + 0.5 * xrange,
                velocities=[0.2],
                period = 0.5,
                open_shutter=True,
                peaklist=peaklist,
            )
            maxlocs.append(peaklist[-1]["WAXS Beamstop"][sam_X.name])
    
    
    print(maxlocs)  # [af2y,af2xm90,af2x0,af2x90,af2x180,af1y,af1xm90,af1x0,af1x90,af1x180]
    accept = input(f"Do you want to apply this correction (y,n)?")
    if accept in ["y", "Y", "yes"]:
        back = False
        for samp in rsoxs_config["bar"]:
            if samp["front"] == False:
                back = True
        correct_bar(maxlocs, include_back=back)
    # bec.disable_plots()
