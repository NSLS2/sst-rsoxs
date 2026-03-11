##
import numpy as np

from rsoxs.configuration_setup.configurations_instrument import load_configuration
from rsoxs.Functions.alignment import (
    load_samp, 
    rotate_now
    )
from rsoxs.HW.energy import set_polarization
from nbs_bl.plans.scans import nbs_list_scan
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.hw import (
    en,
    mir3,
)

import bluesky.plan_stubs as bps
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl




def m3_sweep(
        polarizations = [0, 90],
        energies = None,
        m3_xs = None,
        m3_pitches = None,
        configuration = "WAXSNEXAFS",
        sample_id = "OpenBeam",

):
    """
    Sweeps M3 pitch across different M3 x, energies, and polarizations.
    If the M3 pitch and x at which the maximum flux occurs stays the same across energies, then upstream M2/PGM are well-aligned.
    If not, then the M2/PGM roll may need to be adjusted via the manual wobble stick.

    TODO: Make a version that uses flymax.

    Args:
        polarizations: list of float values between -1 and 180
            List of polarizations (in degrees) to scan.
            Defaults to [0, 90]
        energies: list of float values between 70 and 2200
            List of energies (eV) to scan.
            Defaults to energies_250grating_default or energies_1200grating_default list to span energies covered by grating.
        m3_xs: list of float values
            List of inboard-outboard positions of M3 mirror.
        m3_pitches: list of float values
            List of M3 rotations about vertical axis.
        configuration: str
            Instrument configuration at which to run the scan.
        sample_id: str
            Sample to load before running the scan.



    Returns:
        Sweep of M3 settings across different beamline settings.


    Raises:


    Examples:
        For user beam time startup and before energy calibration, run a smaller subset such as RE(m3_sweep(polarizations=[0], energies=[270], m3_xs=[24.2]))
        
        For commissioning studies and after energy calibration, run the default parameters using RE(m3_sweep()).
        
        
    """

    ## Set input variables
    ## Using late binding method so that any inputs defined in the iPython terminal override defaults.
    if energies is None:
        energies_250grating_default = np.concatenate((
            np.array([90, 110, 130, 150, 200, 250]),
            np.arange(300, 1100, 100)
        ))
        energies_1200grating_default = np.concatenate((
            energies_250grating_default,
            np.arange(1100, 2100, 100)
        ))
        energies = energies_1200grating_default
    if m3_xs is None:
        m3_xs = np.arange(24, 24.5, 0.05)
    if m3_pitches is None:
        m3_pitches = np.arange(7.6, 8, 0.002)

    ## Store previous settings
    m3_x_start = mir3.x.read()['SST 1 Mirror 3 fmb_x_setpoint']["value"] #m3_x_start = 24.2
    m3_pitch_start = mir3.pitch.read()['SST 1 Mirror 3 fmb_pitch_setpoint']["value"] #m3_pitch_start = 7.78

    
    yield from load_configuration(configuration)
    ## TODO: Open slits 2 and 3 at this stage?  And then restore configuration at the end?
    yield from load_samp(sample_id)

    print("Starting M3 sweep.")
    for polarization in polarizations:
        print("Setting polarization: " + str(polarization))
        yield from set_polarization(polarization)
        for energy in energies:
            #if polarization == 90 and energy < 790: continue
            print("Setting energy: " + str(energy) + " eV")
            yield from bps.mv(en, energy)
            for m3_x in m3_xs:
                print("Setting M3 x = " + str(m3_x))
                yield from bps.mv(mir3.x, m3_x)
                yield from nbs_list_scan(mir3.pitch, m3_pitches)


    ## Restore old settings
    yield from set_polarization(0)
    yield from bps.mv(en, 270)
    yield from bps.mv(mir3.x, m3_x_start)
    yield from bps.mv(mir3.pitch, m3_pitch_start)