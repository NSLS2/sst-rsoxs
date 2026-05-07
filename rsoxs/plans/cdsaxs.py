from copy import deepcopy
import numpy as np
import bluesky.plan_stubs as bps
from bluesky.plan_stubs import create, read, save
from bluesky import preprocessors as bpp
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl

RE = bl.run_engine

def cdsaxs_scan(det=None,angle_mot = None,shutter = None,start_angle=50,end_angle=85,exp_time=9,md=None):
    
    waxs_det = bl["waxs_det"]
    sam_Th = bl['sam_Th']
    shutter_control = bl['shutter_control']
    shutter_open_time = bl['shutter_open_time']


    ## Sanitize inputs that can't go directly into inputs
    det = det if det else waxs_det 
    angle_mot = angle_mot if angle_mot else sam_Th 
    shutter = shutter if shutter else shutter_control
    
    _md = deepcopy(dict(RE.md))
    if md == None:
        md = {}
    _md.update(md)
    
    
    _md.update({'plan_info':f'CDSAXS_{start_angle/2}to{end_angle/2}_{exp_time}sec'})
    yield from bps.mv(shutter_open_time,exp_time*1000)
    yield from bps.mv(det.cam.acquire_time, exp_time)
    yield from bps.mv(angle_mot,start_angle)
    old_velo = angle_mot.velocity.get()
    if np.abs(end_angle - start_angle)/old_velo < exp_time:
        yield from bps.mv(angle_mot.velocity,np.abs((end_angle - start_angle)/exp_time))
    @bpp.run_decorator(md=_md)
    @bpp.stage_decorator([det])
    def _inner_scan():
        yield from bps.abs_set(shutter, 1, just_wait=True, group='shutter') # start waiting for the shutter to open
        yield from bps.trigger(det, group='measure') # trigger the detector, which will eventually open the shutter
        yield from bps.wait(group='shutter') # wait for the shutter to open
        yield from bps.abs_set(angle_mot,end_angle,group='measure') # begin motor movement
        yield from bps.wait(group='measure') # wait for the detector to finish
        yield from create('primary')
        reading = (yield from read(det))
        yield from save()
        return reading
    def _cleanup():
        yield from bps.mv(angle_mot.velocity,old_velo)
    return (yield from bpp.contingency_wrapper(_inner_scan(),final_plan=_cleanup))