import bluesky.plan_stubs as bps
import datetime, os
import logging

global no_notifications_until
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from ..HW.slackbot import rsoxs_bot
from nbs_bl.hw import (
    sam_X, 
    sam_Y, 
    sam_Th,
    sam_Z, 
    #BeamStopS, 
    BeamStopW, 
    #Det_S, 
    #Det_W, 
    izero_y, 
    shutter_y
)
from nbs_bl.hw import gratingx, mirror2x, mirror2, grating ## TODO: these should be contained in the energy object, so might not be necessary
from nbs_bl.hw import(
    slits1,
    slits2,
    slits3,
    MC19_disable, 
    MC20_disable, 
    MC21_disable
)
from nbs_bl.printing import run_report

run_report(__file__)

RE = bl.run_engine

def pause_notices(until=None, **kwargs):
    # pause_notices turns off emails on errors either until a specified time or for a specified duration.
    #
    # for set end time, use until = string (compatible with strptime() in datetime)
    #
    # for duration, use parameters for the datetime.timedelta kwargs: hours= minutes= seconds= days=
    #

    global no_notifications_until
    if until is None and len(kwargs) == 0:
        print("You need to specify either a duration or a timeout.")
    elif until is None:
        no_notifications_until = datetime.datetime.now() + datetime.timedelta(**kwargs)
    elif until is not None:
        no_notifications_until = datetime.datetime.strptime(until)


def resume_notices():
    global no_notifications_until

    no_notifications_until = None


def send_notice(subject, msg):
    try:
        rsoxs_bot.send_message(subject + "\n" + msg)
    except Exception:
        pass


def send_notice_plan(subject, msg):
    send_notice(subject, msg)
    yield from bps.sleep(0.1)


def enc_clr_x():
    send_notice(
        "SST had a small problem",
        "the encoder loss has happened on the RSoXS beamline" "\rEverything is probably just fine",
    )
    xpos = sam_X.user_readback.get()
    yield from sam_X.clear_encoder_loss()
    yield from sam_X.home()
    yield from bps.sleep(30)
    yield from bps.mv(sam_X, xpos)


def amp_fault_clear_19():
    send_notice(
        "AmpFault on MC19",
        "Attempting automatic clear",
    )
    # turn on disable to MC19 amps
    yield from bps.mv(MC19_disable,1)
    # wait a second
    yield from bps.sleep(1)
    # enable all MC19 amps
    yield from bps.mv(
        slits1.top.enable,1,
        slits1.bottom.enable,1,
        slits1.inboard.enable,1,
        slits1.outboard.enable,1,
        shutter_y.enable,1,
        izero_y.enable,1,
    )
    # wait a second
    yield from bps.sleep(5)
    # turn off MC19 amps
    yield from bps.mv(MC19_disable,0)


def amp_fault_clear_20():
    send_notice(
        "AmpFault on MC20",
        "Attempting automatic clear",
    )
    # turn on disable to MC19 amps
    yield from bps.mv(MC20_disable,1)
    # wait a second
    yield from bps.sleep(1)
    # enable all MC19 amps
    yield from bps.mv(
        slits2.top.enable,1,
        slits2.bottom.enable,1,
        slits2.inboard.enable,1,
        slits2.outboard.enable,1,
        slits3.top.enable,1,
        slits3.bottom.enable,1,
        slits3.inboard.enable,1,
        slits3.outboard.enable,1,
    )
    # wait a second
    yield from bps.sleep(5)
    # turn off MC19 amps
    yield from bps.mv(MC20_disable,0)


def amp_fault_clear_21():
    send_notice(
        "AmpFault on MC21",
        "Attempting automatic clear",
    )
    # turn on disable to MC19 amps
    yield from bps.mv(MC21_disable,1)
    # wait a second
    yield from bps.sleep(1)
    # enable all MC19 amps
    yield from bps.mv(
        sam_X.top.enable,1,
        sam_Y.bottom.enable,1,
        sam_Th.inboard.enable,1,
        sam_Z.outboard.enable,1,
        #Det_S.enable,1,
        #Det_W.enable,1,
        #BeamStopS.enable,1,
        BeamStopW.enable,1,
    )
    # wait a second
    yield from bps.sleep(5)
    # turn off MC19 amps
    yield from bps.mv(MC21_disable,0)


def enc_clr_x():
    send_notice(
        "SST had a small problem",
        "the encoder loss has happened on the RSoXS beamline" "\rEverything is probably just fine",
    )
    xpos = sam_X.user_readback.get()
    yield from sam_X.clear_encoder_loss()
    yield from sam_X.home()
    yield from bps.sleep(30)
    yield from bps.mv(sam_X, xpos)


def enc_clr_gx():
    send_notice(
        "SST had a small problem",
        "the encoder loss has happened on the RSoXS beamline" "\rEverything is probably just fine",
    )

    yield from gratingx.clear_encoder_loss()
    yield from gratingx.enable()
    yield from mirror2x.enable()
    yield from mirror2.enable()
    yield from grating.enable()


def det_down_notice():
    send_notice(
        f"<@U04EK5L230D> {get_user_slack_tag()} SST-1 detector seems to have failed",  # username for rsoxs slack U016YV35UAJ
        "The temperature is reading below -90C which is a mistake"
        "\rScans have been paused until the detector and IOC are restarted.",
    )


def det_up_notice():
    send_notice("SST-1 detector seems to have recovered", "\rScans should resume shortly.")


def temp_bad_notice():
    send_notice(
        "SST-1 detector seems to be out of temperature range", "\rScans will pause until the detecor recovers."
    )


def temp_ok_notice():
    send_notice(
        bls_email + "," + user_email, "SST-1 detector seems to have recovered", "\rScans should resume shortly."
    )


def beamdown_notice():
    send_notice(
        "SST-1 has lost beam",
        f"{get_user_slack_tag()}\r"
        "Beam to RSoXS has been lost."
        "\rYour scan has been paused automatically."
        "\rNo intervention needed, but thought you might "
        "like to know.",
    )
    yield from bps.null()


def beamup_notice():
    send_notice(
        "SST-1 beam restored",
        f"{get_user_slack_tag()}\r"
        "Beam to RSoXS has been restored."
        "\rYour scan has resumed running."
        "\rIf able, you may want to check the data and "
        "make sure intensity is still OK. "
        "\rOne exposure may have been affected",
    )
    yield from bps.null()


def get_user_slack_tag():
    user_slack_tag = ""
    if "user_slack_tag" in RE.md.keys():
        if type(RE.md["user_slack_tag"]) is list:
            for tag in RE.md["user_slack_tag"]:
                user_slack_tag += f"<@{tag}> "
        else:
            user_slack_tag += f'<@{RE.md["user_slack_tag"]}>'
    return user_slack_tag


class OSEmailHandler(logging.Handler):
    def emit(self, record):
        send_notice(
            f"<@U04EK5L230D> {get_user_slack_tag()} SST has thrown an exception",
            record.getMessage(),
        )  # record.stack_info


class MakeSafeHandler(logging.Handler):
    def emit(self, record):
        ...
        # print('close the shutter here')
        # NOTE: this seems to get run anytime there is any problem with bluesky whatso ever, so nothing dramatic should really be done here
        # @TODO insert code to make instrument 'safe', e.g. close shutter
