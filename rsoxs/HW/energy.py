import bluesky.plan_stubs as bps
import bluesky.plans as bp
from sst_base.energy.soft import (
    base_set_polarization,
)
from nbs_bl.hw import (
    psh4,
    en,
)
from ophyd import EpicsSignal
from nbs_bl.printing import run_report
# from ..startup import bec


run_report(__file__)

#en = EnSimEPUPos("", rotation_motor=sam_Th, name="en")
#en = EnPos("", rotation_motor=sam_Th, name="en")
# en.energy.kind = "hinted"
# en.monoen.kind = "normal"
mono_en = en.monoen


mono_en.read_attrs = ['readback']

#mono_en.tolerance.set(0.02)
epu_gap = en.epugap
#epu_gap.tolerance.set(2)
epu_phase = en.epuphase
#epu_phase.tolerance.set(10)
epu_mode = en.epumode
#en.mir3Pitch.tolerance.set(0.01)
# en.m3offset.kind = "normal"
# mono_en.readback.kind = "hinted"
# mono_en.setpoint.kind = "normal"
# mono_en.grating.kind = "normal"
# mono_en.grating.user_offset.kind = "normal"
# mono_en.gratingx.kind = "normal"
# mono_en.mirror2.kind = "normal"
# mono_en.mirror2.user_offset.kind = "normal"
# mono_en.mirror2x.kind = "normal"
# mono_en.readback.kind = "normal"
# mono_en.kind = "normal"
# mono_en.cff.kind = "normal"
# en.epugap.kind = "normal"
# en.epuphase.kind = "normal"
# en.epumode.kind = "normal"
# en.polarization.kind = "normal"
# en.sample_polarization.kind = "normal"
# en.read_attrs = ["energy", "polarization", "sample_polarization"]
# en.epugap.read_attrs = ["user_readback", "user_setpoint"]
# en.monoen.read_attrs = [
#     "readback",
#     "grating",
#     "grating.user_readback",
#     "grating.user_setpoint",
#     "grating.user_offset",
#     "mirror2",
#     "mirror2.user_readback",
#     "mirror2.user_offset",
#     "mirror2.user_setpoint",
#     "cff",
# ]
# en.monoen.grating.kind = "normal"
# en.monoen.mirror2.kind = "normal"
# en.monoen.gratingx.kind = "normal"
# en.monoen.mirror2x.kind = "normal"
# en.epugap.kind = "normal"
# en.epugap.kind = "normal"
# en.read_attrs = ['readback']

#Mono_Scan_Start_ev = en.monoen.Scan_Start_ev
#Mono_Scan_Stop_ev = en.monoen.Scan_Stop_ev
#Mono_Scan_Speed_ev = en.monoen.Scan_Speed_ev
#Mono_Scan_Start = en.monoen.Scan_Start
#Mono_Scan_Stop = en.monoen.Scan_Stop

def set_polarization(pol):
    yield from base_set_polarization(pol, en)


def base_grating_to_250(mono_en, en):
    type = mono_en.gratingx.readback.get()
    if "250l/mm" in type:
        print("the grating is already at 250 l/mm")
        return 0  # the grating is already here
    print("Moving the grating to 250 l/mm.  This will take a minute...")
    yield from psh4.close()
    yield from bps.abs_set(mono_en.gratingx, 2, wait=True)
    # yield from bps.sleep(60)
    # yield from bps.mv(mirror2.user_offset, 0.04) #0.0315)
    # yield from bps.mv(grating.user_offset, -0.0874)#-0.0959)
    # yield from bps.mv(en.m3offset, 7.90)
    yield from bps.mv(mono_en.cff, 1.385)
    yield from bps.mv(en, 270)
    yield from psh4.open()
    print("the grating is now at 250 l/mm signifigant higher order")
    return 1


def base_grating_to_1200(mono_en, en):
    type = mono_en.gratingx.readback.get()
    if "1200" in type:
        print("the grating is already at 1200 l/mm")
        return 0  # the grating is already here
    print("Moving the grating to 1200 l/mm.  This will take a minute...")
    yield from psh4.close()
    yield from bps.abs_set(mono_en.gratingx, 9, wait=True)
    # yield from bps.sleep(60)
    # yield from bps.mv(mirror2.user_offset, 0.2044) #0.1962) #0.2052) # 0.1745)  # 8.1264)
    # yield from bps.mv(grating.user_offset, 0.0769) #0.0687) # 0.0777) # 0.047)  # 7.2964)  # 7.2948)#7.2956
    yield from bps.mv(mono_en.cff, 1.7)
    # yield from bps.mv(en.m3offset, 7.791)
    yield from bps.mv(en, 270)
    yield from psh4.open()
    print("the grating is now at 1200 l/mm")
    return 1


def base_grating_to_rsoxs(mono_en, en):
    type = mono_en.gratingx.readback.get()
    if "RSoXS" in type:
        print("the grating is already at RSoXS")
        return 0  # the grating is already here
    print("Moving the grating to RSoXS 250 l/mm.  This will take a minute...")
    yield from psh4.close()
    yield from bps.abs_set(mono_en.gratingx, 10, wait=True)
    # yield from bps.sleep(60)
    # yield from bps.mv(mirror2.user_offset, 0.2044) #0.1962) #0.2052) # 0.1745)  # 8.1264)
    # yield from bps.mv(grating.user_offset, 0.0769) #0.0687) # 0.0777) # 0.047)  # 7.2964)  # 7.2948)#7.2956
    # yield from bps.mv(mono_en.cff, 1.7)
    # yield from bps.mv(en.m3offset, 7.87)
    yield from bps.mv(en, 270)
    yield from psh4.open()
    print("the grating is now at RSoXS 250 l/mm with low higher order")
    return 1



def grating_to_1200(hopgx=None,hopgy=None,hopgtheta=None):
    moved = yield from base_grating_to_1200(mono_en, en)
    try:
        x = float(hopgx)
        y = float(hopgy)
        th = float(hopgtheta)
    except Exception:
        x = None
        y = None
        th = None
    if moved and isinstance(x,float) and isinstance(y,float) and isinstance(th,float):
        yield from calibrate_energy(x,y,th)
        # ensave = en.energy.setpoint.get()
        # xsave = sam_X.user_setpoint.get()
        # ysave = sam_Y.user_setpoint.get()
        # thsave = sam_Th.user_setpoint.get()
        # bec.enable_plots()
        # Sample_TEY.kind='hinted'
        # yield from bps.mv(sam_X,hopgx,sam_Y,hopgy,sam_Th,hopgtheta)
        # yield from bps.mv(en.polarization, 0)
        # yield from bps.mv(en, 291.65)
        # yield from bps.sleep(1)
        # yield from bps.mv(en, 291.65)
        # yield from bps.sleep(1)
        # yield from bps.mv(en, 291.65)
        # yield from bps.mv(en.polarization, 0)
        # yield from bps.mv(shutter_control,1)
        # yield from bp.rel_scan([Sample_TEY],grating,-0.05,.05,mirror2,-0.05,.05,201)
        # yield from bps.mv(shutter_control,0)
        # yield from bps.mv(sam_X,xsave,sam_Y,ysave,sam_Th,thsave)
        # yield from bps.sleep(5)
        # newoffset = en.monoen.grating.get()[0] - bec.peaks.max['RSoXS Sample Current'][0]
        # if -0.05 < newoffset < 0.05 :
        #     yield from bps.mvr(grating.user_offset,newoffset,mirror2.user_offset,newoffset)
        # yield from bps.mv(en, ensave)
        # bec.disable_plots()
        # Sample_TEY.kind='normal'


def grating_to_250(hopgx=None,hopgy=None,hopgtheta=None):
    moved = yield from base_grating_to_250(mono_en, en)
    try:
        x = float(hopgx)
        y = float(hopgy)
        th = float(hopgtheta)
    except Exception:
        x = None
        y = None
        th = None
    if moved and isinstance(x,float) and isinstance(y,float) and isinstance(th,float):
        yield from calibrate_energy(x,y,th)



def grating_to_rsoxs(hopgx=None,hopgy=None,hopgtheta=None):
    moved = yield from base_grating_to_rsoxs(mono_en, en)
    try:
        x = float(hopgx)
        y = float(hopgy)
        th = float(hopgtheta)
    except Exception:
        x = None
        y = None
        th = None
    if moved and isinstance(x,float) and isinstance(y,float) and isinstance(th,float):
        yield from calibrate_energy(x,y,th)


# def calibrate_energy(x,y,th):
#     ensave = en.energy.setpoint.get()
#     xsave = sam_X.user_setpoint.get()
#     ysave = sam_Y.user_setpoint.get()
#     thsave = sam_Th.user_setpoint.get()
#     #bec.enable_plots()
#     Sample_TEY.kind='hinted'
#     yield from bps.mv(sam_X,x,sam_Y,y,sam_Th,th)
#     yield from bps.mv(en.polarization, 90)
#     yield from bps.mv(en, 291.65)
#     yield from bps.sleep(1)
#     yield from bps.mv(en, 291.65)
#     yield from bps.sleep(1)
#     yield from bps.mv(en, 291.65)
#     yield from bps.mv(shutter_control,1)
#     yield from bp.rel_scan([Sample_TEY],grating,-0.5,.5,mirror2,-0.5,.5,201)
#     yield from bps.mv(shutter_control,0)
#     yield from bps.sleep(5)
#     newoffset = en.monoen.grating.get()[0] - bec.peaks.max['RSoXS Sample Current'][0]
#     if -0.45 < newoffset < 0.45 :
#         yield from bps.mvr(grating.user_offset,newoffset,mirror2.user_offset,newoffset)
#     yield from bps.mv(en, 291.65)
#     yield from bps.sleep(1)
#     yield from bps.mv(en, 291.65)
#     yield from bps.sleep(1)
#     yield from bps.mv(en, 291.65)
#     yield from bps.mv(shutter_control,1)
#     yield from bp.rel_scan([Sample_TEY],grating,-0.02,.02,mirror2,-0.02,.02,101)
#     yield from bps.mv(shutter_control,0)
#     yield from bps.mv(sam_X,xsave,sam_Y,ysave,sam_Th,thsave)
#     yield from bps.sleep(5)
#     newoffset = en.monoen.grating.get()[0] - bec.peaks.max['RSoXS Sample Current'][0]
#     if -0.019 < newoffset < 0.019 :
#         yield from bps.mvr(grating.user_offset,newoffset,mirror2.user_offset,newoffset)
#     yield from bps.mv(en, ensave)
#     bec.disable_plots()
#     Sample_TEY.kind='normal'

speed_offset_factor = 30

def get_gap_offset(start,stop,speed):
    if stop>start:
        return speed * speed_offset_factor
    else:
        return -speed * speed_offset_factor





### new code to test the undulator fly scanning
'''
interesting PVs:
SR:C07-ID:G1A{SST1:1}CalculateSpline.PROC
SR:C07-ID:G1A{SST1:1}EScan-Speed-SP
SR:C07-ID:G1A{SST1:1}EScan-Speed-RB
SR:C07-ID:G1A{SST1:1}FlyMove-Mtr-SP
SR:C07-ID:G1A{SST1:1}FlyMove-Mtr-Go.PROC
SR:C07-ID:G1A{SST1:1}FlyMove-Mtr.STOP
SR:C07-ID:G1A{SST1:1}FlyMove-Speed-SP
SR:C07-ID:G1A{SST1:1}FlyMove-Speed-RB

Energy and Gap arrays which are used for the spline calculation:
SR:C07-ID:G1A{SST1:1}FlyLUT-Energy-RB
SR:C07-ID:G1A{SST1:1}FlyLUT-Gap-RB
SR:C07-ID:G1A{SST1:1}FlyLUT-Energy-SP
SR:C07-ID:G1A{SST1:1}FlyLUT-Gap-SP

Process to calculate a new spline:
SR:C07-ID:G1A{SST1:1}CalculateSpline.PROC

For Energy Move:

SR:C07-ID:G1A{SST1:1}FlyMove-Mtr-SP # setpoint of move final position
SR:C07-ID:G1A{SST1:1}FlyMove-Mtr-Go.PROC # go
SR:C07-ID:G1A{SST1:1}FlyMove-Mtr.STOP # stop
SR:C07-ID:G1A{SST1:1}FlyMove-Speed-SP # setpoint speed
SR:C07-ID:G1A{SST1:1}FlyMove-Speed-RB # readback speed

SR:C07-ID:G1A{SST1:1}FlyMove-Mtr.MOVN # moving
'''

