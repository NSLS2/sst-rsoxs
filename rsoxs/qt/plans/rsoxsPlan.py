from qtpy.QtWidgets import (
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
)
from qtpy.QtCore import Signal, Qt
from bluesky_queueserver_api import BPlan, BFunc
from nbs_gui.plans.planParam import DynamicComboParam
from nbs_gui.plans.nbsPlan import NBSPlanWidget


class RSoXSParam(DynamicComboParam):
    signal_update_region = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rsoxs_plans = {}
        self.input_widget.currentIndexChanged.connect(self.update_region)

    def update_options(self, rsoxs_plans):
        current_text = self.input_widget.currentText()
        self.rsoxs_plans = rsoxs_plans
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)
        sorted_keys = sorted(rsoxs_plans, key=lambda x: rsoxs_plans[x]["name"])
        for key in sorted_keys:
            plan_info = rsoxs_plans[key]
            display_label = plan_info.get("name", key)
            self.input_widget.addItem(str(display_label), userData=key)

        index = self.input_widget.findText(current_text)
        self.input_widget.setCurrentIndex(index if index >= 0 else 0)

    def update_region(self):
        key = self.input_widget.currentData()
        plan_info = self.rsoxs_plans.get(key, {})
        region = str(plan_info.get("region", ""))
        self.signal_update_region.emit(region)

    def make_region_label(self):
        label = QLabel("")
        self.signal_update_region.connect(label.setText)
        return label

    def get_params(self):
        if self.input_widget.currentIndex() != 0:
            data = self.input_widget.currentData()
            print(f"Returning RSOXS {data}")
            return {"plan": data}
        return {}


class RSoXSPlanWidget(NBSPlanWidget):
    signal_update_rsoxs = Signal(object)
    display_name = "RSoXS"

    def __init__(self, model, parent=None):
        print("Initializing RSoXS")

        super().__init__(
            model,
            parent,
            "dummy",
            layout_style=2,
            dwell={
                "type": "spinbox",
                "args": {"minimum": 0.1, "value_type": float, "default": 1},
                "label": "Dwell Time per Step (s)",
            },
            n_exposures={
                "type": "spinbox",
                "args": {"minimum": 1, "value_type": int, "default": 1},
                "label": "Number of Exposures",
            },
        )
        self.signal_update_rsoxs.connect(self.update_rsoxs)
        self.user_status.register_signal("RSOXS_PLANS", self.signal_update_rsoxs)
        print("RSoXS Initialized")

        # Add Load RSOXS button
        self.load_rsoxs_button = QPushButton("Load RSoXS regions from file", self)
        self.load_rsoxs_button.clicked.connect(self.load_rsoxs_file)
        self.basePlanLayout.addWidget(self.load_rsoxs_button)

    def setup_widget(self):
        super().setup_widget()

        self.rsoxs_plans = {}
        self.edge_selection = RSoXSParam("edge", "RSoXS Scan", "Select RSoXS Plan", parent=self)
        self.scan_widget.add_param(self.edge_selection, 0)
        self.scan_widget.add_row(QLabel("Scan Region"), self.edge_selection.make_region_label(), 1)
        self.user_status.register_signal("RSOXS_PLANS", self.signal_update_rsoxs)
        self.user_status.register_signal("RSOXS_PLANS", self.edge_selection.signal_update_options)

    def load_rsoxs_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("TOML files (*.toml)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                item = BFunc("load_rsoxs", file_path)
                try:
                    # Load the RSOXS plans
                    self.run_engine_client._client.function_execute(item)

                    # Wait for function execution to complete
                    def condition(status):
                        return status["manager_state"] == "idle"

                    try:
                        self.run_engine_client._wait_for_completion(
                            condition=condition, msg="load RSOXS plans", timeout=10
                        )
                        # Now update the environment
                        self.run_engine_client.environment_update()
                    except Exception as wait_ex:
                        QMessageBox.warning(
                            self,
                            "RSOXS Load Warning",
                            f"RSOXS plans may not be fully loaded: {str(wait_ex)}",
                            QMessageBox.Ok,
                        )
                    return True
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "RSOXS Load Error",
                        f"Failed to load {file_path}: {str(e)}",
                        QMessageBox.Ok,
                    )
                    return False

    def check_plan_ready(self):
        """
        Check if all selections have been made and emit the plan_ready signal if they have.
        """
        if self.sample_select.check_ready() and self.edge_selection.check_ready():
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def update_rsoxs(self, plan_dict):
        self.rsoxs_plans = plan_dict
        self.edge_selection.signal_update_options.emit(self.rsoxs_plans)
        self.widget_updated.emit()

    def create_plan_items(self):
        params = self.get_params()
        plan = params.pop("plan")
        samples = params.pop("samples", [{}])
        items = []
        for s in samples:
            item = BPlan(plan, **s, **params)
            items.append(item)
        return items
