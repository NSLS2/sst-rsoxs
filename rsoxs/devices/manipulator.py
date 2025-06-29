import copy

from nbs_bl.devices import Manipulator4AxBase
from sst_base.motors import PrettyMotorFMBODeadbandFlyer
from ophyd import Component as Cpt
from nbs_bl.geometry.bars import AbsoluteBar


class RSoXSBar(AbsoluteBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    

def ManipulatorBuilderRSOXS(prefix, *, name, **kwargs):
    class Manipulator(Manipulator4AxBase):
        x = Cpt(PrettyMotorFMBODeadbandFlyer, "X}Mtr", kind="hinted")
        y = Cpt(PrettyMotorFMBODeadbandFlyer, "Y}Mtr", kind="hinted")
        z = Cpt(PrettyMotorFMBODeadbandFlyer, "Z}Mtr", kind="hinted")
        r = Cpt(PrettyMotorFMBODeadbandFlyer, "Yaw}Mtr", kind="hinted")

    holder = RSoXSBar()
    origin = (0, 0, 464)
    manip = Manipulator(prefix, name=name, attachment_point=origin, holder=holder, **kwargs)

    return manip
