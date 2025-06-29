from matplotlib import pyplot as plt
import numpy as np
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import pandas as pd
from bluesky.callbacks.fitting import PeakStats
from bluesky.preprocessors import subs_wrapper
from bluesky import preprocessors as bpp
from bluesky.run_engine import Msg
from nbs_bl.hw import (
    en,
    grating,
    mirror2,
    psh10,
    slitsc,
    slits1,
    izero_mesh,
    slits2,
    shutter_control,
    shutter_enable,
    gv27a,
    sam_Th, 
    sam_Y,
    rsoxs_ll_gpwr,
    gvll,
    beamstop_waxs,
    waxs_det,
    DownstreamLargeDiode_int,
    Sample_TEY,
    Sample_TEY_int,
    MC19_disable,
    MC20_disable,
    MC21_disable,
    gv28,
)
from ..HW.energy import (
    mono_en,
    grating_to_1200,
    grating_to_250,
    grating_to_rsoxs,
    set_polarization,
    epu_gap,
    epu_phase,
    epu_mode
)
from .alignment import load_configuration,load_samp
from ..HW.detectors import set_exposure
# from ..startup import bec
from nbs_bl.printing import run_report
from nbs_bl.gGrEqns import get_mirror_grating_angles, find_best_offsets
from .fly_alignment import fly_max
from .energyscancore import cdsaxs_scan
from .rsoxs_plans import do_rsoxs

run_report(__file__)


def buildeputable(
    start,
    stop,
    step,
    widfract,
    startinggap=14000,
    phase=0,
    mode="L",
    grat="1200",
    name="test",
):
    ens = np.arange(start, stop, step)
    gaps = []
    gapsbs = []
    ensout = []
    heights = []
    heightsbs = []
    #izero_mesh.kind = "hinted"
    #Beamstop_SAXS.kind = "hinted"
    mono_en.kind = "hinted"
    epu_gap.kind = "hinted"
    # startinggap = epugap_from_energy(ens[0]) #get starting position from existing table
    # if grat == "1200":
    #     yield from grating_to_1200(2.0,-6.3,0.0)
    # elif grat == "250":
    #     yield from grating_to_250(2.0,-6.3,0.0)
    # elif grat == "rsoxs":
    #     yield from grating_to_rsoxs(2.0,-6.3,0.0)
    # bec.enable_plots()

    plt.close()
    plt.close()
    plt.close()
    plt.close()

    # yield from bps.mv(sam_Y,30)
    if mode == "C":
        yield from bps.mv(epu_mode, 0)
    elif mode == "CW":
        yield from bps.mv(epu_mode, 1)
    elif mode == "L3":
        yield from bps.mv(epu_mode, 3)
    else:
        yield from bps.mv(epu_mode, 2)
    yield from bps.mv(epu_phase, phase)

    yield from bps.mv(epu_gap.tolerance,0)

    count = 0
    peaklist = []
    flip=False
    for energy in ens:
        #yield from bps.mv(epu_gap, max(14000, startinggap - 500 * widfract))
        #yield from bps.mv(shutter_enable, 0)
        #yield from bps.mv(shutter_control, 1)
        if not flip:
            startgap = min(99500, max(14000, startinggap - 500 * widfract))
            endgap = min(100000, max(15000, startinggap + 2500 * widfract))
            flip = True
        else:
            endgap = min(99500, max(14000, startinggap - 500 * widfract))
            startgap = min(100000, max(15000, startinggap + 2500 * widfract))
            flip = False
        
        yield from bps.mv(mono_en, energy,en.scanlock, False,epu_gap,startgap)
        yield from fly_max(
            [izero_mesh, beamstop_waxs, DownstreamLargeDiode_int],
            [
                "RSoXS Au Mesh Current",
                "WAXS Beamstop",
            ],
            epu_gap,
            startgap,
            endgap,
            [200],
            10,
            True,
            True,
            peaklist,
            end_on_max=False
        )
        startinggap = peaklist[-1]["RSoXS Au Mesh Current"]["en_epugap"]
        gapbs = peaklist[-1]["WAXS Beamstop"]["en_epugap"]
        height = peaklist[-1]["RSoXS Au Mesh Current"]["RSoXS Au Mesh Current"]
        heightbs = peaklist[-1]["WAXS Beamstop"]["WAXS Beamstop"]
        gaps.append(startinggap)
        gapsbs.append(gapbs)
        heights.append(height)
        heightsbs.append(heightbs)
        ensout.append(mono_en.position)
        data = {
            "Energies": ensout,
            "EPUGaps": gaps,
            "PeakCurrent": heights,
            "EPUGapsBS": gapsbs,
            "PeakCurrentBS": heightsbs,
        }
        dataframe = pd.DataFrame(data=data)
        dataframe.to_csv("/nsls2/data/sst/legacy/RSoXS/EPUdata_2023Nov_" + name + ".csv")
        count += 1
        if count > 20:
            count = 0
            plt.close()
            plt.close()
            plt.close()
            plt.close()
    plt.close()
    plt.close()
    plt.close()
    plt.close()
    print(peaklist)
    # print(ens,gaps)


def do_some_eputables_2023_en():

    yield from load_configuration("WAXSNEXAFS")
    yield from bps.mv(slits1.hsize, 1)
    yield from bps.mv(slits2.hsize, 1)
    
    phase_from_angle_poly= [78.672,870.98,-24.036,0.44117,-0.0042377,1.7304e-05]
    def phase_from_angle(angle):
        phase = 0
        phase += 870.98 * angle**1
        phase += -24.036 * angle**2
        phase += 0.44117 * angle**3
        phase += -0.0042377 * angle**4
        phase += 1.7304e-05 * angle**5
        return min(29500,max(0,phase))
    def starting_energy(angle):
        energy = 80.934
        energy += -0.91614 * angle**1
        energy += 0.39635 * angle**2
        energy += -0.020478 * angle**3
        energy += 0.00069047 * angle**4
        energy += -1.5413e-05 * angle**5
        energy += 2.1448e-07 * angle**6
        energy += -1.788e-09 * angle**7
        energy += 8.162e-12 * angle**8
        energy += -1.5545e-14 * angle**9
        return energy+5

    #angles = np.linspace(18,10,4)
    #up = list(np.geomspace(0.5,45,9))
    #down = list(90-np.geomspace(0.5,40,9))
    #down.reverse()
    #angles = [0,90] + up + down
    # linear polarizations 0-90
    #for angle in angles:
    for angle in [0,90]:
        yield from buildeputable(starting_energy(angle)*3, 2200, 50, 3, 14000, phase_from_angle(angle), "L", "1200", f"linear3x_{angle}deg_r5")
    # circular polarizations
    yield from buildeputable(300, 2200, 50, 3, 14000, 15000, "C", "1200", f"Circ3_r5")
    yield from buildeputable(300, 2200, 50, 3, 14000, 15000, "CW", "1200", f"CWCirc3_r5")

    for angle in [30,60,45,10,80]:
        yield from buildeputable(starting_energy(angle)*3, 2200, 50, 5, 14000, phase_from_angle(angle), "L", "1200", f"linear3x_{angle}deg_r5")
    
    #angles = up + down

    # linear polarizations 90-180
    #for angle in [0,15,30,45,60,75,85]:
    #    yield from buildeputable(starting_energy(angle), 1300, 20, 3, 14000, phase_from_angle(angle), "L3", "rsoxs", f"linear_{180-angle}deg_r6")


    #third harmonics


    # # linear polarizations 0-90
    # for angle in angles:
    #     yield from buildeputable(1000, 2200, 50, 5, 14000, phase_from_angle(angle), "L", "1200", f"linear3_{angle}deg_r5")

    
    # angles = up + down

    # # linear polarizations 90-180
    # for angle in angles:
    #     yield from buildeputable(starting_energy(angle)*3, 2200, 30, 5, 14000, phase_from_angle(angle), "L3", "1200", f"linear3_{180-angle}deg_r6")

    # 1200l/pp from 400 to 1400 eV



#    yield from buildeputable(200, 1300, 10, 2, 20922, 8000, "L", "1200", "mL8_1200")

#    yield from buildeputable(200, 1300, 10, 2, 23704, 0, "L3", "1200", "m3L0_1200")

# yield from buildeputable(80, 500, 10, 2, 14000, 0, "L", "250", "mL0_250")
# yield from buildeputable(145, 500, 10, 2, 14000, 29500, "L", "250", "mL29p5_250")

# yield from buildeputable(80, 500, 10, 2, 14000, 0, "L3", "250", "m3L0_250")


def Scan_izero_peak(startingen, widfract):
    ps = PeakStats("en_energy", "RSoXS Au Mesh Current")
    yield from subs_wrapper(
        tune_max(
            [izero_mesh, beamstop_waxs, DownstreamLargeDiode_int],
            "RSoXS Au Mesh Current",
            mono_en,
            min(2100, max(72, startingen - 10 * widfract)),
            min(2200, max(90, startingen + 50 * widfract)),
            1,
            25,
            2,
            True,
            md={"plan_name": "energy_tune"},
        ),
        ps,
    )
    print(ps.cen)
    return ps


def buildeputablegaps(start, stop, step, widfract, startingen, name, phase, grating):
    gaps = np.arange(start, stop, step)
    ens = []
    gapsout = []
    heights = []
    beamstop_waxs.kind = "hinted"
    DownstreamLargeDiode_int.kind = "hinted"
    izero_mesh.kind = "hinted"
    epu_gap.kind = "hinted"
    # startinggap = epugap_from_energy(ens[0]) #get starting position from existing table

    count = 0

    if grating == "1200":
        yield from grating_to_1200()

    elif grating == "250":
        yield from grating_to_250()

    yield from bps.mv(epu_phase, phase)

    for gap in gaps:
        yield from bps.mv(epu_gap, gap)
        yield from bps.mv(mono_en, max(72, startingen - 10 * widfract))
        peaklist = []
        yield from tune_max(
            [izero_mesh, beamstop_waxs, DownstreamLargeDiode_int],
            "RSoXS Au Mesh Current",
            mono_en,
            min(2100, max(72, startingen - 10 * widfract)),
            min(2200, max(90, startingen + 50 * widfract)),
            1,
            25,
            2,
            True,
            md={"plan_name": "energy_tune"},
            peaklist=peaklist,
        )

        ens.append(peaklist[0])
        heights.append(peaklist[1])
        gapsout.append(epu_gap.position)
        startingen = peaklist[0]
        data = {"Energies": ens, "EPUGaps": gapsout, "PeakCurrent": heights}
        dataframe = pd.DataFrame(data=data)
        dataframe.to_csv("/mnt/zdrive/EPUdata_2021_" + name + ".csv")
        count += 1
        if count > 20:
            count = 0
            plt.close()
            plt.close()
            plt.close()
    plt.close()
    plt.close()
    plt.close()


def do_2020_eputables():
    # yield from buildeputablegaps(15000, 55000, 500, 1.5, 75, 'H1phase02',0)
    # yield from bps.mv(mono_en,600)
    # yield from bps.mv(mono_en,400)
    # yield from bps.mv(mono_en,200)
    # yield from buildeputablegaps(15000, 50000, 500, 1.5, 150, 'H1phase295002',29500)
    # yield from bps.mv(mono_en,600)
    # yield from bps.mv(mono_en,400)
    # yield from bps.mv(mono_en,200)
    # yield from buildeputablegaps(15000, 50000, 500, 2, 3*75, 'H3phase02',0)
    # yield from bps.mv(mono_en,900)
    # yield from bps.mv(mono_en,600)
    # yield from bps.mv(mono_en,400)
    # yield from bps.mv(epu_mode,0)
    yield from buildeputablegaps(15000, 40000, 500, 2, 200, "H1Circphase150002", 15000)
    yield from bps.mv(mono_en, 800)
    yield from buildeputablegaps(15000, 30000, 500, 2, 600, "H3Circphase150002", 15000)


# yield from bps.mv(epu_mode,2)


def do_2023_eputables():
    izero_mesh.kind = "hinted"
    beamstop_waxs.kind = "hinted"
    DownstreamLargeDiode_int.kind = "hinted"
    mono_en.readback.kind = "hinted"
    mono_en.kind = "hinted"
    mono_en.read_attrs = ["readback"]
    # bec.enable_plots()  # TODO: this will work, but not needed - need to move all plotting to a seperate app
    yield from load_configuration("WAXSNEXAFS")
    yield from bps.mv(slits1.hsize, 1)
    yield from bps.mv(slits2.hsize, 1)
    yield from bps.mv(epu_mode, 3)

    yield from buildeputablegaps(14000, 35000, 500, 1, 80, "_Feb2023_phase4000_0", 0, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase29500_1200", 29500, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase26000_1200", 26000, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase23000_1200", 23000, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase21000_1200", 21000, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase18000_1200", 18000, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase15000_1200", 15000, 1200)
    yield from buildeputablegaps(14000, 30000, 500, 2, 150, "_Feb2023_phase12000_1200", 12000, 1200)
    yield from buildeputablegaps(14000, 35000, 500, 1, 80, "_Feb2023_phase8000_1200", 8000, 1200)
    yield from buildeputablegaps(14000, 35000, 500, 1, 80, "_Feb2023_phase4000_1200", 4000, 1200)
    yield from buildeputablegaps(14000, 35000, 500, 1, 80, "_Feb2023_phase4000_1200", 4000, 1200)


def tune_max(
    detectors,
    signals,
    motor,
    start,
    stop,
    min_step,
    num=10,
    step_factor=3.0,
    snake=False,
    peaklist=[],
    *,
    md=None,
):
    r"""
    plan: tune a motor to the maximum of signal(motor)

    Initially, traverse the range from start to stop with
    the number of points specified.  Repeat with progressively
    smaller step size until the minimum step size is reached.
    Rescans will be centered on the signal maximum
    with original scan range reduced by ``step_factor``.

    Set ``snake=True`` if your positions are reproducible
    moving from either direction.  This will not
    decrease the number of traversals required to reach convergence.
    Snake motion reduces the total time spent on motion
    to reset the positioner.  For some positioners, such as
    those with hysteresis, snake scanning may not be appropriate.
    For such positioners, always approach the positions from the
    same direction.

    Note:  if there are multiple maxima, this function may find a smaller one
    unless the initial number of steps is large enough.

    Parameters
    ----------
    detectors : Signal
        list of 'readable' objects
    signals : string
        detector fields whose output is to maximize
        (the first will be the primary, but secondardy maxes will be recorded)
    motor : object
        any 'settable' object (motor, temp controller, etc.)
    start : float
        start of range
    stop : float
        end of range, note: start < stop
    min_step : float
        smallest step size to use.
    num : int, optional
        number of points with each traversal, default = 10
    step_factor : float, optional
        used in calculating new range after each pass

        note: step_factor > 1.0, default = 3
    snake : bool, optional
        if False (default), always scan from start to stop
    md : dict, optional
        metadata

    Examples
    --------
    Find the center of a peak using synthetic hardware.

     from ophyd.sim import SynAxis, SynGauss
     motor = SynAxis(name='motor')
     det = SynGauss(name='det', motor, 'motor',
                    center=-1.3, Imax=1e5, sigma=0.05)
     RE(tune_max([det], "det", motor, -1.5, -0.5, 0.01, 10))
    """
    signal = signals[0]
    if min_step <= 0:
        raise ValueError("min_step must be positive")
    if step_factor <= 1.0:
        raise ValueError("step_factor must be greater than 1.0")
    try:
        (motor_name,) = motor.hints["fields"]
    except (AttributeError, ValueError):
        motor_name = motor.name
    _md = {
        "detectors": [det.name for det in detectors],
        "motors": [motor.name],
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "motor": repr(motor),
            "start": start,
            "stop": stop,
            "num": num,
            "min_step": min_step,
        },
        "plan_name": "tune_max",
        "hints": {},
    }
    _md.update(md or {})
    try:
        dimensions = [(motor.hints["fields"], "primary")]
    except (AttributeError, KeyError):
        pass
    else:
        _md["hints"].setdefault("dimensions", dimensions)

    low_limit = min(start, stop)
    high_limit = max(start, stop)

    @bpp.stage_decorator(list(detectors) + [motor])
    @bpp.run_decorator(md=_md)
    def _tune_core(start, stop, num, signal, peaklist):
        next_pos = start
        step = (stop - start) / (num - 1)
        peak_position = None
        cur_I = None
        max_I = -1e50  # for peak maximum finding (allow for negative values)
        max_xI = 0
        cur_sigI = None
        max_I_signals = {}
        max_xI_signals = {}
        for sig in signals:
            max_I_signals[sig] = -1e50
        while abs(step) >= min_step and low_limit <= next_pos <= high_limit:
            yield Msg("checkpoint")
            yield from bps.mv(motor, next_pos)
            ret = yield from bps.trigger_and_read(detectors + [motor])
            cur_I = ret[signal]["value"]
            position = ret[motor_name]["value"]
            if cur_I > max_I:
                max_I = cur_I
                max_xI = position
                max_ret = ret
            for sig in signals:
                cur_sigI = ret[sig]["value"]
                if cur_sigI > max_I_signals[sig]:
                    max_I_signals[sig] = cur_sigI
                    max_xI_signals[sig] = position

            next_pos += step
            in_range = min(start, stop) <= next_pos <= max(start, stop)

            if not in_range:
                if max_I == -1e50:
                    return
                peak_position = max_xI  # maxiumum
                max_xI, max_I = 0, 0  # reset for next pass
                new_scan_range = (stop - start) / step_factor
                start = np.clip(peak_position - new_scan_range / 2, low_limit, high_limit)
                stop = np.clip(peak_position + new_scan_range / 2, low_limit, high_limit)
                if snake:
                    start, stop = stop, start
                step = (stop - start) / (num - 1)
                next_pos = start
                # print("peak position = {}".format(peak_position))
                # print("start = {}".format(start))
                # print("stop = {}".format(stop))

        # finally, move to peak position
        if peak_position == 0:
            peak_position = start
        if peak_position is not None:
            # improvement: report final peak_position
            # print("final position = {}".format(peak_position))
            yield from bps.mv(motor, peak_position)
        peaklist.append([max_ret, max_xI_signals, max_I_signals])
        return [max_ret, max_xI_signals, max_I_signals]

    return (yield from _tune_core(start, stop, num, signal, peaklist))


def stability_scans(num):
    scans = np.arange(num)
    for scan in scans:
        yield from bps.mv(en, 200)
        yield from bp.scan([izero_mesh], en, 200, 1400, 1201)


# settings for 285.3 eV 1.6 C 1200l/mm gold Aug 1, 2020
# e 285.3
# en.monoen.grating.set_current_position(-7.494888000531973)
# en.monoen.mirror2.set_current_position(-6.085536389355577)

# {'en_monoen_grating_user_offset': {'value': -0.31108245265481216,
#   'timestamp': 1596294657.763531}}

# {'en_monoen_mirror2_user_offset': {'value': -1.158546028874075,
#   'timestamp': 1596294681.080148}}


#def isvar_scan():
#    polarizations = [0, 90]
#    angles = [10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30]
#    exps = [0.01, 0.01, 0.05, 0.05, 0.1, 1, 1, 1, 1]
#    for angle, exp in zip(angles, exps):
#        set_exposure(exp)
#        yield from bps.mv(sam_Th, 90 - angle)
#        for polarization in polarizations:
#            yield from bps.mv(en.polarization, polarization)
#            yield from bp.scan([waxs_det], en, 270, 670, 5)


def vent():
    yield from psh10.close()
    yield from gv28.close()
    yield from gv27a.close()
    yield from bps.mv(sam_Y, 349)

    print("waiting for you to close the load lock gate valve")
    print("Please also close the small manual black valve on the back of the load lock now")
    while gvll.state.get() is 1:
        gvll.read()  # attempt at a fix for problem where macro hangs here.
        bps.sleep(1)
    print("TEM load lock closed - turning off loadlock gauge")
    yield from bps.mv(rsoxs_ll_gpwr, 0)
    print("Should be safe to begin vent by pressing right most button of BOTTOM turbo controller once")
    print("")



def reset_amps():
    yield from bps.mv(MC19_disable, 1, MC20_disable, 1, MC21_disable, 1)
    yield from bps.sleep(5)
    yield from bps.mv(MC19_disable, 0, MC20_disable, 0, MC21_disable, 0)

#[200,250,270,280,282,283,284,285,286,287,288,500,535,800]

def do_cdsaxs(energies, samples):
    ## If a reduction in X-ray dose is needed, then adjust the slitsc aperture size and not the exposure time.  The 9 s exposure time is necessary to ensure X-ray exposure is delivered at all angles.
    yield from bps.mv(slitsc,-1.05) # big flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-57,end_angle=-80,exp_time=9,md={'plan_name':f'CD_high_{energy}'})
    yield from bps.mv(slitsc,-0.05) # mid flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-57,end_angle=-80,exp_time=9,md={'plan_name':f'CD_mid1_{energy}'})
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-65,end_angle=-88,exp_time=9,md={'plan_name':f'CD_mid2_{energy}'})
    yield from bps.mv(slitsc,-0.01) # least flux
    for samp in samples:
        yield from load_samp(samp)
        for energy in energies:
            yield from bps.mv(en,energy)
            yield from cdsaxs_scan(angle_mot=sam_Th,det=waxs_det,start_angle=-65,end_angle=-88,exp_time=9,md={'plan_name':f'CD_low_{energy}'})
    yield from bps.mv(slitsc,-3.05) # all flux
    for samp in samples:
        yield from load_samp(samp)
        yield from bps.mv(sam_Th,-70)
        yield from do_rsoxs(edge=energies,frames=1,exposure=.1,md={'plan_name':f'CD_20deg'})


def ramp_temp_test(temp,ramp_rate,interval,energies,pols,name):
    yield from bps.mv(tem_tempstage.ramp_rate,ramp_rate)
    status = (yield from bps.abs_set(tem_tempstage.setpoint,temp,group='temp'))
    while not status.done:
        yield from bps.sleep(interval)
        for energy in energies:
            for pol in pols:
                yield from bps.mv(en,energy,en.polarization,pol)
                temp = tem_tempstage.readback.get()
                RE.md['sample_id']=f'{name}_{energy}eV__{temp}C'
                RE.md['sample_name']=f'{name}_{energy}eV__{temp}C'
                print(f'taking an image with name {RE.md["sample_name"]}')
                yield from bps.count([waxs_det])


