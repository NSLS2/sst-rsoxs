from bluesky import Msg

def skinnystage(obj):
    yield Msg("skinnystage", obj)

def skinnyunstage(obj):
    yield Msg("skinnyunstage", obj)