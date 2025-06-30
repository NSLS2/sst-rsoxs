import copy

from nbs_bl.devices import Manipulator4AxBase
from sst_base.motors import PrettyMotorFMBODeadbandFlyer
from ophyd import Component as Cpt
from nbs_bl.geometry.bars import AbsoluteBar

from ..configuration_setup.configuration_load_save_sanitize import load_configuration_spreadsheet_local, get_sample_dictionary_nbs_format_from_rsoxs_config


class RSoXSBar(AbsoluteBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read_sample_file(self, filename):
        configuration = load_configuration_spreadsheet_local(filename)
        bar_dict = get_sample_dictionary_nbs_format_from_rsoxs_config(configuration=configuration)
        return bar_dict
    

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
