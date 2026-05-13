from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from datetime import datetime
import os
from os.path import join
from rsoxs.HW.contingencies import turn_off_checks

md = bl.md
md['data_session'] = '111111'
md['cycle'] = '2026-2'
md['username'] = 'simuser'
md['start_datetime'] = datetime.now().isoformat()
md['saf'] = '222222'
md['proposal'] = {
    'proposal_id': '111111',
    'title': 'Test Proposal',
    'type': 'GU',
    'pi_name': 'PI, Test'
}

def get_proposal_directory(asset_name):
    write_path_template = "/nsls2/data/sst/proposals"
    date_template = "%Y/%m/%d/"
    proposal_path = f"{md['cycle']}/{md['data_session']}/assets/{asset_name}"
    write_path = join(write_path_template, proposal_path, date_template)
    formatter = datetime.now().strftime
    write_path = formatter(write_path)
    return write_path

def create_proposal_directory(asset_name):
    write_path = get_proposal_directory(asset_name)
    if not os.path.exists(write_path):
        os.makedirs(write_path)
    return write_path

for detector in bl.all_standard_pros.devices.values():
    if hasattr(detector, "tiff"):
        camera_name = detector.tiff.camera_name
        create_proposal_directory(camera_name)

waxs_det = bl["waxs_det"]
waxs_det.cam.temperature_actual.set(-80)
waxs_det.cam.shutter_mode.set(1)

from ophyd._pyepics_shim import caput

caput("XF:07ID1-ES:1{GE:2}cam1:ShutterCloseEPICS.OUT$", "XF:07IDB-CT{DIODE-Local:1}OutPt01:Data-Sel CP")
caput("XF:07ID1-ES:1{GE:2}cam1:ShutterOpenEPICS.OUT$", "XF:07IDB-CT{DIODE-Local:1}OutPt01:Data-Sel CP")
caput("XF:07ID1-ES:1{GE:2}cam1:ShutterCloseEPICS.OVAL", 0)
caput("XF:07ID1-ES:1{GE:2}cam1:ShutterOpenEPICS.OVAL$", 1)
turn_off_checks()