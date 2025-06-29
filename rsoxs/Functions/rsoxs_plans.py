import bluesky.plan_stubs as bps
from bluesky.preprocessors import finalize_decorator
import datetime
from copy import deepcopy
from nbs_bl.printing import run_report, boxed_text
from rsoxs_scans.rsoxs import dryrun_rsoxs_plan
from .alignment import load_sample, load_configuration, move_to_location, spiralsearch, rotate_sample
from nbs_bl.hw import (
    tem_tempstage,
)
from ..HW.signals import High_Gain_diode_i400, setup_diode_i400
from .energyscancore import NEXAFS_fly_scan_core, new_en_scan_core, NEXAFS_step_scan_core
from ..startup import RE
from ..HW.slackbot import rsoxs_bot

run_report(__file__)























## Below is Eliot's old code, above is simplified code

## TODO: remove dictionary, never used
actions = {
    "load_configuration",  # high level load names RSoXS configuration
    "rsoxs_scan_core",  # high level run a single RSoXS plan
    "temp",  # change the temperature
    "spiral_scan_core",  # high spiral scan a sample
    "move",  # move an ophyd object
    "load_sample",  # high level load a sample
    "message",  # message the user - no action
    "diode_low",  # set diodes range setting to low
    "diode_high",  # set diode range setting to high
    "nexafs_scan_core",  # high level run a single NEXAFS scan
    "nexafs_step_scan_core",  # high level run a single step-based NEXAFS scan
    "error",  # raise an error - should never get here.
}
motors = {"temp_ramp_rate": tem_tempstage.ramp_rate}





def run_queue_step(step):
    if step["acq_index"] < 1:  # we haven't seen a second queue step, so we don't mention it
        print(f"\n----- starting queue step {step['queue_step']+1}-----\n")
    else:
        print(f"\n----- starting queue step {step['queue_step']+1} in acquisition # {step['acq_index']+1}-----\n")
    print(step["description"])
    """
    ## Causing issues during early 2025-1 testing, so disabling for now.
    if step["action"] == "diode_low":
        return (yield from High_Gain_diode_i400())
    if step["action"] == "diode_high":
        return (yield from setup_diode_i400())
    """
    if step["action"] == "load_configuration":
        return (yield from load_configuration(step["kwargs"]["configuration"]))
    if step["action"] == "load_sample":
        return (yield from load_sample(step["kwargs"]["sample"]))
    if step["action"] == "temp":
        if step["kwargs"]["wait"]:
            return (yield from bps.mv(tem_tempstage, step["kwargs"]["temp"]))
        else:
            return (yield from bps.mv(tem_tempstage.setpoint, step["kwargs"]["temp"]))
    if step["action"] == "temp":
        if step["kwargs"]["wait"]:
            return (yield from bps.mv(tem_tempstage, step["kwargs"]["temp"]))
        else:
            return (yield from bps.mv(tem_tempstage.setpoint, step["kwargs"]["temp"]))
    if step["action"] == "move":
        return (yield from bps.mv(motors[step["kwargs"]["motor"]], step["kwargs"]["position"]))
        # use the motors look up table above to get the motor object by name
    if step["action"] == "spiral_scan_core":
        return (yield from spiralsearch(**step["kwargs"])) #return (yield from spiralsearch(**step["kwargs"]))
    if step["action"] == "nexafs_scan_core":
        return (yield from NEXAFS_fly_scan_core(**step["kwargs"]))
    if step["action"] == "nexafs_step_scan_core":
        return (yield from NEXAFS_step_scan_core(**step["kwargs"]))
    if step["action"] == "rsoxs_scan_core":
        return (yield from new_en_scan_core(**step["kwargs"]))
    if step["acq_index"] < 1:
        print(f"\n----- finished queue step {step['queue_step']+1}-----\n")
    else:
        print(f"\n----- finished queue step {step['queue_step']+1} in acquisition # {step['acq_index']+1}-----\n")


# plans for manually running a single rsoxs scan in the terminal or making your own plans
## TODO: This is unnecessarily redundant.  Either cut this out or find a way to incorporate into the workflow
def do_rsoxs(md=None, **kwargs):
    """
    inputs:
        edge,
        exposure_time = 1,
        frames='full',
        ratios=None,
        repeats =1,
        polarizations = [0],
        angles = None,
        grating='rsoxs',
        diode_range='high',
        temperatures=None,
        temp_ramp_speed=10,
        temp_wait=True,
        md=None,
    """

    _md = deepcopy(dict(RE.md))
    if md == None:
        md = {}
    _md.update(md)
    outputs = dryrun_rsoxs_plan(md=_md, **kwargs)
    for i, out in enumerate(outputs):
        out["acq_index"] = i
        out["queue_step"] = 0
    print("Starting RSoXS plan")
    for queue_step in outputs:
        yield from run_queue_step(queue_step)
    print("End of RSoXS plan")


