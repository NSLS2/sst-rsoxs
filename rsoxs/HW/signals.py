from ophyd.status import StatusTimeoutError
from nbs_bl.printing import run_report
from bluesky import plan_stubs as bps
from bluesky import FailedStatus
from datetime import datetime as datet
from nbs_bl.hw import (
    beamstop_waxs,
    #Beamstop_SAXS,
    izero_mesh,
    Sample_TEY_int,
    ring_current,
    diode_i400_cap,
    Slit1_i400_enable,
    diode_i400_enable,
    Slit1_i400_npnts,
    Slit1_i400_read_time,
    diode_i400_npnts,
    Slit1_i400_mode,
    diode_i400_mode,
    Slit1_i400_accum,
    diode_i400_accum,
    diode_i400_read_time,
    diode_i400_PDU,
)

run_report(__file__)

default_sigs = [
    beamstop_waxs,
    izero_mesh,
    Sample_TEY_int,
    ring_current,
]


def setup_slit1_i400():
    yield from bps.mv(Slit1_i400_enable, "Disabled")
    try:
        yield from bps.mv(Slit1_i400_cap, "10pF", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(Slit1_i400_npnts, 200, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(Slit1_i400_read_time, 0.0002, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(Slit1_i400_mode, "Trigger Count", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(Slit1_i400_accum, "Interpolate", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(Slit1_i400_enable, "Enabled", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass


def setup_diode_i400():
    yield from bps.mv(diode_i400_enable, "Disabled")
    try:
        yield from bps.mv(diode_i400_cap, "1000pF", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_npnts, 100, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_mode, "Trigger Count", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_read_time, 0.0002, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_accum, "Interpolate", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_enable, "Enabled", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass


def High_Gain_diode_i400():
    yield from bps.mv(diode_i400_enable, "Disabled")
    try:
        yield from bps.mv(diode_i400_cap, "10pF", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_npnts, 20, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_mode, "Trigger Count", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_read_time, 0.01, timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_accum, "Interpolate", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass
    try:
        yield from bps.mv(diode_i400_enable, "Enabled", timeout=1)
    except FailedStatus:
        pass
    except StatusTimeoutError:
        pass


def power_cycle_diode_i400():
    yield from bps.mv(diode_i400_PDU, "Off")
    yield from bps.sleep(2)
    yield from bps.mv(diode_i400_PDU, "On")


def reset_diodes():
    yield from power_cycle_diode_i400()
    yield from bps.sleep(5)
    yield from setup_diode_i400()


#def check_diodes():
#    if datet.timestamp(datet.now()) - Beamstop_SAXS.read()["SAXS Beamstop"]["timestamp"] > 1:
#        yield from reset_diodes()
