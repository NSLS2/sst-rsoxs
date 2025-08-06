from nbs_gui.plans.base import BasicPlanWidget
from nbs_gui.plans.planParam import DynamicComboParam, ParamGroup, LineEditParam
from qtpy.QtCore import Slot


class RSoXSConfigurationParam(DynamicComboParam):
    def update_options(self, options):
        print(f"Updating options for RSoXSConfigurationParam to {options}")
        if options is not None:
            super().update_options(list(options.keys()))


class RSoXSBeamlineSetupParams(ParamGroup):
    def __init__(self, model, parent=None):
        print("Setting up RSoXSBeamlineSetupParams")
        super().__init__(parent, "Beamline Setup")
        self.config_param = RSoXSConfigurationParam(
            "configuration_name", "Configuration", "Select a configuration", "Select a configuration"
        )
        self.add_param(self.config_param)
        self.add_param(LineEditParam("energy", float, "Energy", "Energy to set at plan start"))
        self.user_status = model.user_status
        self.user_status.register_signal("RSoXS_Config", self.config_param.signal_update_options)


class RSoXSSetupWidget(BasicPlanWidget):

    def __init__(self, model, parent=None):
        super().__init__(
            model, parent, plans="load_configuration", params=[RSoXSConfigurationParam(model, parent)]
        )
