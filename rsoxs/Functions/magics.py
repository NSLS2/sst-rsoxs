# This file should only be run if ipython is being used ... put that check here!
from IPython.core.magic import register_line_magic
import bluesky.plan_stubs as bps
from IPython.terminal.prompts import Prompts, Token
import datetime
from nbs_bl.hw import (
    en,
    slitsc,
    sam_Y,
    sam_Th,
    sam_Z,
    sam_X,
    BeamStopS,
    BeamStopW,
    Det_W,
    Det_S,
    shutter_y,
    #Izero_ds,
    izero_y,
    sam_viewer,
)

from rsoxs.configuration_setup.configurations_instrument import all_out #from .configurations import all_out
from ..HW.detectors import (
    set_exposure,
    waxs_det,
    snapshot,
    exposure,
)
from nbs_bl.plans.scans import nbs_count
from ..Functions.alignment import sample
from ..startup import RE
from ..HW.energy import set_polarization
from nbs_bl.printing import run_report, boxed_text


run_report(__file__)


@register_line_magic
def x(line):
    RE(sam_X.status_or_rel_move(line))


@register_line_magic
def y(line):
    RE(sam_Y.status_or_rel_move(line))


@register_line_magic
def z(line):
    RE(sam_Z.status_or_rel_move(line))


@register_line_magic
def th(line):
    RE(sam_Th.status_or_rel_move(line))


@register_line_magic
def bsw(line):
    RE(BeamStopW.status_or_rel_move(line))


@register_line_magic
def bss(line):
    RE(BeamStopS.status_or_rel_move(line))


@register_line_magic
def dw(line):
    RE(Det_W.status_or_rel_move(line))


@register_line_magic
def ds(line):
    RE(Det_S.status_or_rel_move(line))


@register_line_magic
def motors(line):
    boxed_text(
        "RSoXS Motor Locations",
        (
            sam_X.where()
            + "  x"
            + "\n"
            + sam_Y.where()
            + "  y"
            + "\n"
            + sam_Z.where()
            + "  z"
            + "\n"
            + sam_Th.where()
            + "  th"
            + "\n"
            + BeamStopW.where()
            + "  bsw"
            + "\n"
            + BeamStopS.where()
            + "  bss"
            + "\n"
            + Det_W.where()
            + "  dw"
            + "\n"
            # + Det_S.where()
            # + "  ds"
            # + "\n"
            + shutter_y.where()
            + "\n"
            + izero_y.where()
            + "\n"
            + Izero_ds.where()
            + "\n"
            + slitsc.where()
            + "\n"
            + sam_viewer.where()
            + "\n"
        ),
        "lightgray",
        shrink=True,
    )


del x, y, z, th, ds, dw, bss, bsw, motors


# Energy


@register_line_magic
def e(line):
    try:
        loc = float(line)
    except:
        boxed_text("Beamline Energy", en.where(), "lightpurple", shrink=True)
    else:
        RE(bps.mv(en, loc))
        boxed_text("Beamline Energy", en.where(), "lightpurple", shrink=True)


del e


@register_line_magic
def pol(line):
    try:
        loc = float(line)
    except:
        boxed_text("Beamline Polarization", en.where(), "lightpurple", shrink=True)
    else:
        RE(set_polarization(loc))
        boxed_text("Beamline Polarization", en.where(), "lightpurple", shrink=True)


del pol


### Configurations


@register_line_magic
def nmode(line):
    RE(all_out())


del nmode


@register_line_magic
def exp(line):
    try:
        secs = float(line)
    except:
        boxed_text("Exposure times", exposure(), "lightgreen", shrink=True)
    else:
        if secs > 0.001 and secs < 1000:
            set_exposure(secs)


del exp


@register_line_magic
def binning(line):
    try:
        bins = int(line)
    except:
        boxed_text(
            "Pixel Binning",
            "   " + waxs_det.binning(), #+ "\n   " + saxs_det.binning(),
            "lightpurple",
            shrink=True,
        )
    else:
        if bins > 0 and bins < 100:
            # saxs_det.set_binning(bins, bins)
            waxs_det.set_binning(bins, bins)


del binning


@register_line_magic
def temp(line):
    boxed_text(
        "Detector cooling",
        "   " + waxs_det.cooling_state() ,#+ "\n   " + saxs_det.cooling_state(),
        "blue",
        shrink=True,
        width=95,
    )


del temp


@register_line_magic
def cool(line):
    # saxs_det.cooling_on()
    waxs_det.cooling_on()


del cool


@register_line_magic
def warm(line):
    # saxs_det.cooling_off()
    waxs_det.cooling_off()


del warm


# snapshots


@register_line_magic
def snap(line):
    try:
        secs = float(line)
    except:
        RE(nbs_count(num=1, use_2d_detector=True, delay=0, dwell=1)) #RE(snapshot())
    else:
        if secs > 0 and secs < 10:
            RE(nbs_count(num=1, use_2d_detector=True, delay=0, dwell=secs)) #RE(snapshot(secs))


del snap


@register_line_magic
def snapsaxs(line):
    try:
        secs = float(line)
    except:
        RE(snapshot(detn="saxs"))
    else:
        if secs > 0 and secs < 10:
            RE(snapshot(secs, detn="saxs"))


del snapsaxs

    
@register_line_magic
def snapwaxs(line):
    try:
        secs = float(line)
    except:
        RE(snapshot(detn="waxs"))
        #RE(nbs_count(num=1, use_2d_detector=True, delay=0, dwell=1)) 
    else:
        if secs > 0 and secs < 10:
            RE(snapshot(secs, detn="waxs"))
            #RE(nbs_count(num=1, use_2d_detector=True, delay=0, dwell=secs)) 
            ## TODO: migrate to nbs_count once it registers teh correct sample


del snapwaxs


@register_line_magic
def snaps(line):
    try:
        num = int(line)
    except:
        RE(snapshot())
    else:
        if num > 0 and num < 100:
            RE(snapshot(count=num))


del snaps


# metadata (sample/user)


@register_line_magic
def md(line):
    sample()



del md


class RSoXSPrompt(Prompts):
    def in_prompt_tokens(self, cli=None):
        if RE.md.get("analysis_dir", None) and len(RE.md["analysis_dir"]) > 0: #if len(RE.md["analysis_dir"]) > 0: ## 20250123 - ran into error while loading sample
            RSoXStoken = (
                Token.Prompt,
                f"RSoXS {RE.md['analysis_dir']}",
            )
        else:
            RSoXStoken = (Token.OutPrompt, "RSoXS (define metadata before scanning)")
        return [
            RSoXStoken,
            (Token.Prompt, " ["),
            (Token.PromptNum, str(self.shell.execution_count)),
            (Token.Prompt, "]: "),
        ]


ip = get_ipython()
ip.prompts = RSoXSPrompt(ip)


def beamline_status():
    sample()
    boxed_text(
        "Detector status",
        exposure()
        + "\n   "
        # + saxs_det.binning()
        # + "\n   "
        + waxs_det.binning()
        + "\n   "
        # + saxs_det.cooling_state()
        # + "\n   "
        + waxs_det.cooling_state()
        + "\n   WAXS "
        + waxs_det.shutter(),
        # + "\n   SAXS "
        # + saxs_det.shutter(),
        "lightblue",
        80,
        shrink=False,
    )


@register_line_magic
def status(line):
    beamline_status()


del status
