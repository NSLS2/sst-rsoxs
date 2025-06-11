from nbs_bl.devices import Manipulator4AxBase
from sst_base.motors import PrettyMotorFMBODeadbandFlyer
from ophyd import Component as Cpt
from nbs_bl.geometry.bars import AbsoluteBar
from rsoxs.configuration_setup.configuration_load_save import load_configuration_spreadsheet_local


class RSoXSBar(AbsoluteBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read_sample_file(self, filename):
        configuration = load_configuration_spreadsheet_local(filename)
        bar_dict = {}
        for sample_dict in configuration:
            sample_id = sample_dict.pop("sample_id")
            sample_dict["name"] = sample_dict.get("sample_name", "")
            location = sample_dict.get("location")
            coordinates = []
            for key in ["x", "y", "z", "th"]:
                for loc in location:
                    if loc.get("motor") == key:
                        coordinates.append(loc.get("position"))
                        break
            if len(coordinates) != 4:
                raise ValueError(f"Sample {sample_dict['name']} has {len(coordinates)} positions, expected 4")
            sample_dict["position"] = {"coordinates": coordinates}
            sample_dict["origin"] = "absolute"
            sample_dict["description"] = sample_dict.get("sample_desc", "")
            bar_dict[sample_id] = sample_dict
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
