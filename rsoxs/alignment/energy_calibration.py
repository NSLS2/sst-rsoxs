import numpy as np
import bluesky.plan_stubs as bps
from nbs_bl.hw import (
    en,
    grating,
    mirror2,
    slits1,
    slits2,
    slits3,
    Sample_TEY_int,
)
from nbs_bl.gGrEqns import get_mirror_grating_angles, find_best_offsets
from nbs_bl.plans.scans import nbs_list_scan, nbs_energy_scan
from rsoxs.HW.energy import set_polarization
from ..plans.default_energy_parameters import energy_list_parameters
from .fly_alignment import rsoxs_fly_max
from ..Functions.alignment import load_samp, rotate_now
from ..configuration_setup.configurations_instrument import load_configuration



## Copying Eliot's tune_pgm function and just using Jamie's new fly_max function
def calibrate_pgm_offsets(
    cs=[1.4, 1.35, 1.35],
    ms=[1, 1, 2],
    energy=291.65,
    pol=90,
    k=250, ## Grating l/mm
    detector=None,
    signal="RSoXS Sample Current",
    grat_off_search = 0.08,
    grating_rb_off = 0,
    mirror_rb_off = 0,
    search_ratio = 30,
    scan_time = 30,
):
    # RE(tune_pgm(cs=[1.35,1.37,1.385,1.4,1.425,1.45],ms=[1,1,1,1,1],energy=291.65,pol=90,k=250))
    # RE(tune_pgm(cs=[1.55,1.6,1.65,1.7,1.75,1.8],ms=[1,1,1,1,1],energy=291.65,pol=90,k=1200))

    detector = detector if detector else Sample_TEY_int  ## Cannot have device in function definition for gui

    yield from bps.mv(en.polarization, pol)
    yield from bps.mv(en, energy)
    detector.kind = "hinted"
    mirror_measured = []
    grating_measured = []
    energy_measured = []
    m_measured = []
    # bec.enable_plots()
    for cff, m_order in zip(cs, ms):
        m_set, g_set = get_mirror_grating_angles(energy, cff, k, m_order)
        print(f'setting cff to {cff} for a mirror with k={k} at {m_order} order')
        print("Setting mirror2 to: " + str(m_set))
        m_set += mirror_rb_off
        g_set += grating_rb_off
        yield from bps.mv(grating.velocity, 0.1, mirror2.velocity, 0.1)
        yield from bps.sleep(1)
        yield from bps.mv(grating, g_set, mirror2, m_set)
        yield from bps.sleep(1)
        peaklist = []
        yield from rsoxs_fly_max(
            detectors=[detector], ## TODO: might be good to save out I0 mesh signal as well because then we can see the maxima in the I0 lining up with the maxima in TEY signal.
            motor=grating,
            start=g_set - grat_off_search,
            stop=g_set + grat_off_search,
            velocities=[grat_off_search*2/scan_time, grat_off_search*2/(search_ratio * scan_time), grat_off_search*2/(search_ratio**2 * scan_time)],
            period = 0.5,
            snake=False,
            peaklist=peaklist,
            range_ratio=search_ratio,
            open_shutter=True,
            rb_offset=grating_rb_off,
            stream=False
        )
        grating_measured.append(peaklist[0][signal][grating.name] - grating_rb_off )
        mirror_measured.append(mirror2.read()[mirror2.name]["value"] - mirror_rb_off)
        energy_measured.append(291.65)
        m_measured.append(m_order)
    print(f"mirror positions: {mirror_measured}")
    print(f"grating positions: {grating_measured}")
    print(f"energy positions: {energy_measured}")
    print(f"orders: {m_measured}")
    fit = find_best_offsets(mirror_measured, grating_measured, m_measured, energy_measured, k)
    print(fit)
    accept = input("Accept these values and set the offset (y/n)? ")
    if accept in ["y", "Y", "yes"]:
        yield from bps.mvr(mirror2.user_offset, -fit.x[0], grating.user_offset, -fit.x[1])
    # bec.disable_plots()
    detector.kind = "normal"
    return fit











## The functions below work, but they did not change energy calibration 20251201

def scan_pgm_angles_open_beam(
    lines_per_mm_pgm = 250,
    polarizations = [90, 90, 90, 90, 90], #polarizations = np.full(shape = 5, fill_value = 90),
    energies = [291.65, 291.65, 291.65, 291.65, 291.65], #energies = np.full(shape = 5, fill_value = 291.65),
    cffs = [1.35, 1.4, 1.45, 1.5, 1.55],
    diffraction_orders = [1, 1, 1, 1, 1], #diffraction_orders = np.full(shape = 5, fill_value = 1),
    sample_ids = ["HOPG", "HOPG", "HOPG", "HOPG", "HOPG"], #sample_ids = np.full(5, "HOPG"),
    sample_angles = [20, 20, 20, 20, 20],#sample_angles = np.full(shape = 5, fill_value = 20),
    radius_search_window = 0.08,
    number_points = 100,
):

    """
    Similar to scan_pgm_angles, but only running the open-beam portion of it to mimic scans run by the calibrate_pgm_offsets function.
    """


    for scan in ["reference"]:
            for (
                polarization, 
                energy,
                cff,
                diffraction_order,
                sample_id,
                sample_angle,
            ) in zip(
                    polarizations, 
                    energies,
                    cffs,
                    diffraction_orders,
                    sample_ids,
                    sample_angles,
            ):
                ## Load beamline configuration and sample
                yield from bps.mv(en.polarization, polarization)
                yield from bps.mv(en, energy)
                m2_angle, pgm_angle = get_mirror_grating_angles(en_eV = energy, 
                                                                cff = cff, 
                                                                k_invmm = lines_per_mm_pgm, 
                                                                m = diffraction_order)
                yield from bps.mv(grating.velocity, 0.1, mirror2.velocity, 0.1)
                yield from bps.sleep(1)
                yield from bps.mv(grating, pgm_angle, mirror2, m2_angle)
                yield from bps.sleep(1)
                print(
                    "Set beam polarization = " + str(polarization) + "°, "
                    + "energy = " + str(energy) + " eV, "
                    + "M2 angle = " + str(m2_angle) + "°, "
                    + "PGM angle = " + str(pgm_angle) + "°, "
                    + "CFF = " + str(cff) + ", "
                    + "diffraction order = " + str(diffraction_order) + ", "
                    + "for PGM with " + str(lines_per_mm_pgm) + " lines per mm."
            )

                ## Generate list of motor positions
                ## Ad hoc list of PGM angles to scan based on what was run during calibrate_pgm_offsets 20251201
                if cff > 1.44 and cff < 1.46:
                        grating_angles_to_scan = np.array([-3.63514117, -3.63497026, -3.63480355, -3.63467924, -3.63452837,
                                                        -3.63439711, -3.63428617, -3.63417645, -3.63399415, -3.63387483,
                                                        -3.63370501, -3.63357371, -3.63346538, -3.63324208, -3.63311979,
                                                        -3.63300885, -3.63286154, -3.63269948, -3.63255347, -3.63240687,
                                                        -3.63228579, -3.63213521, -3.63203496, -3.63185743, -3.63174373,
                                                        -3.63158946, -3.63146944, -3.63131714, -3.63117439, -3.6310161 ,
                                                        -3.63088274, -3.63070211, -3.63060585, -3.63041797, -3.63024543,
                                                        -3.63009967, -3.62998299, -3.62983719, -3.62965542, -3.62955702,
                                                        -3.6294095 , -3.62926881, -3.62912393, -3.6290277 , -3.62886082,
                                                        -3.62877109])
                if cff > 1.49 and cff < 1.51:
                        grating_angles_to_scan = np.array([-3.53136105, -3.53111777, -3.53099497, -3.53083488, -3.53074695,
                                                        -3.53055115, -3.53043879, -3.53032354, -3.53017564, -3.53003151,
                                                        -3.52983156, -3.52969393, -3.52947232, -3.52939235, -3.52920426,
                                                        -3.52904379, -3.52891194, -3.52875759, -3.52864297, -3.52852336,
                                                        -3.52835207, -3.52824055, -3.52808297, -3.52795951, -3.52785184,
                                                        -3.5277029 , -3.52754649, -3.52737474, -3.52724969, -3.5271284 ,
                                                        -3.52700162, -3.52685746, -3.52671911, -3.52659326, -3.52643589,
                                                        -3.52630794, -3.52616444, -3.52603733, -3.52586282, -3.52573583,
                                                        -3.52563542, -3.52545294, -3.5253687 , -3.52524319, -3.52506826,
                                                        -3.52499743])
                if cff > 1.54 and cff < 1.56:
                        grating_angles_to_scan = np.array([-3.44419616, -3.44401201, -3.44388193, -3.44374254, -3.44360989,
                                                        -3.44342377, -3.4433063 , -3.44311787, -3.44302865, -3.44288104,
                                                        -3.44271026, -3.44255214, -3.44242503, -3.44229561, -3.44215924,
                                                        -3.44202236, -3.44188272, -3.44175623, -3.44158931, -3.4414767 ,
                                                        -3.44133383, -3.44118744, -3.44102315, -3.44092018, -3.44080124,
                                                        -3.44062459, -3.44052569, -3.44035767, -3.44024213, -3.44010303,
                                                        -3.43995132, -3.43983544, -3.43972631, -3.43958101, -3.43940536,
                                                        -3.43927377, -3.43910978, -3.43900333, -3.43887374, -3.43871088,
                                                        -3.43857606, -3.43843478, -3.43826882, -3.43814435, -3.43801791,
                                                        -3.43786829])
                
                

                if scan == "sample":
                    yield from load_samp(sample_id)
                    yield from rotate_now(sample_angle)
                    print("Loaded sample_id = " + str(sample_id) + ", sample angle = " + str(sample_angle))
                if scan == "reference":
                    yield from load_samp("OpenBeam")
                    print("Loaded sample_id = OpenBeam")

                ## Perform scan
                yield from nbs_list_scan(grating, grating_angles_to_scan)




def scan_pgm_angles(
    lines_per_mm_pgm = 250,
    polarizations = [90, 90, 90, 90, 90], #polarizations = np.full(shape = 5, fill_value = 90),
    energies = [291.65, 291.65, 291.65, 291.65, 291.65], #energies = np.full(shape = 5, fill_value = 291.65),
    cffs = [1.35, 1.4, 1.45, 1.5, 1.55],
    diffraction_orders = [1, 1, 1, 1, 1], #diffraction_orders = np.full(shape = 5, fill_value = 1),
    sample_ids = ["HOPG", "HOPG", "HOPG", "HOPG", "HOPG"], #sample_ids = np.full(5, "HOPG"),
    sample_angles = [20, 20, 20, 20, 20],#sample_angles = np.full(shape = 5, fill_value = 20),
    radius_search_window = 0.08,
    number_points = 100,
):
    """
    Runs scans to generate calibration data for M2 and plane grating monochromator (PGM) angle offsets.
    Allows flexibility to scan multiple samples at multiple optics conditions.
    Runs corresponding open-beam scans to allow double-normalization of sample scans such that any signal distortions (e.g., due to upstream optics contamination) would be corrected.

    Number of scans is equal to the number of elements in the polarizations, energies, cffs, diffraction orders, sample_ids, and sample_angles lists.
    All of these lists should have identical lengths.
    Note, cannot use np.full to define the defaults because numpy arrays cannot be evaluated with ast.literal_eval().
    
    Args:
        lines_per_mm_pgm: int
            Lines per mm for the PGM used.
        polarizations: list of float values
            Beam polarizations during each scan.
            Defaults to 90°, such that the sample-frame polarization is always 90° regardless of the sample angle.
        energies: list of float values
            Nominal energies (eV) during each scan.
            Defaults to 291.65 eV, which is used for HOPG.
        cffs: list of float values
            Constant of fixed focus (CFF) values during each scan.
            Defaults to [1.35, 1.4, 1.45, 1.5, 1.55], such that it is centered around 1.45, at which RSoXS operates.
        diffraction_orders: list of int values
            Beam diffraction orders during each scan.
            Defaults to diffraction order of 1, as higher orders have not been properly located yet.
        sample_ids: list of string values
            List of samples to be run during each scan.
            Defaults to HOPG, which has sharp, intense peak at 291.65 eV.
        sample_angles: list of float values
            Angles at which sample is rotated during each scan.
            Defaults to 20° (70° sample bar angle) such that TEY samples get a large beam footprint.
        radius_search_window: float
            Defines the range of PGM angles to scan (+/- radius_search_widow from the initial PGM angle).
            Defaults to 0.8°.
        number_points: int
            Number of points to scan.
            Adjust to more finely locate maxima.
            Defaults to 100.

    Returns: 

    Raises:

    Examples:
    """

    for scan in ["sample", "reference"]:
        for (
             polarization, 
             energy,
             cff,
             diffraction_order,
             sample_id,
             sample_angle,
        ) in zip(
                 polarizations, 
                 energies,
                 cffs,
                 diffraction_orders,
                 sample_ids,
                 sample_angles,
        ):
            ## Load beamline configuration and sample
            yield from bps.mv(en.polarization, polarization)
            yield from bps.mv(en, energy)
            m2_angle, pgm_angle = get_mirror_grating_angles(en_eV = energy, 
                                                            cff = cff, 
                                                            k_invmm = lines_per_mm_pgm, 
                                                            m = diffraction_order)
            yield from bps.mv(grating.velocity, 0.1, mirror2.velocity, 0.1)
            yield from bps.sleep(1)
            yield from bps.mv(grating, pgm_angle, mirror2, m2_angle)
            yield from bps.sleep(1)
            print(
                  "Set beam polarization = " + str(polarization) + "°, "
                  + "energy = " + str(energy) + " eV, "
                  + "M2 angle = " + str(m2_angle) + "°, "
                  + "PGM angle = " + str(pgm_angle) + "°, "
                  + "CFF = " + str(cff) + ", "
                  + "diffraction order = " + str(diffraction_order) + ", "
                  + "for PGM with " + str(lines_per_mm_pgm) + " lines per mm."
           )

            ## Generate list of motor positions
            grating_angles_to_scan = np.linspace(
                start = pgm_angle - radius_search_window,
                stop = pgm_angle + radius_search_window,
                num = number_points,
            )

            if scan == "sample":
                yield from load_samp(sample_id)
                yield from rotate_now(sample_angle)
                print("Loaded sample_id = " + str(sample_id) + ", sample angle = " + str(sample_angle))
            if scan == "reference":
                yield from load_samp("OpenBeam")
                print("Loaded sample_id = OpenBeam")

            ## Perform scan
            yield from nbs_list_scan(grating, grating_angles_to_scan)





def correct_m2_pgm_offsets(
    m2_angles,
    pgm_angles,
    diffraction_orders = [1, 1, 1, 1, 1], #diffraction_orders = np.full(shape = 5, fill_value = 1),
    energies = [291.65, 291.65, 291.65, 291.65, 291.65], #energies = np.full(shape = 5, fill_value = 291.65),
    lines_per_mm_pgm = 250,
):
    """
    Corrects M2 and PGM offsets using the parameters found during calibraiton scans.

    Args:
        m2_angles: list of float values
            M2 angles during each calibration scan.
        pgm_angles: list of float values
            PGM angles during each calibration scan.
        diffraction_orders: list of int values
            Beam diffraction orders during each calibration scan.
            Defaults to diffraction order of 1, as higher orders have not been properly located yet.
        energies: list of float values
            Nominal energies (eV) during each calibration scan.
            Defaults to 291.65 eV, which is used for HOPG.
        lines_per_mm_pgm: int
            Lines per mm for the PGM used during calibration scans.

    Returns: 

    Raises:

    Examples:
    """

    fit = find_best_offsets(
        mirror_pitches = m2_angles, 
        grating_pitches = pgm_angles, 
        mguesses = diffraction_orders, 
        eVs = energies,
        k_invmm = lines_per_mm_pgm,
    )
    print(fit)
    accept = input("Accept these values and set the offset (y/n)? ")
    if accept in ["y", "Y", "yes"]:
        yield from bps.mvr(mirror2.user_offset, -fit.x[0], grating.user_offset, -fit.x[1])
    return fit












def energy_resolution_series(
     sample_id = "HOPG",
     energy_parameters = "carbon_NEXAFS",
     slit1_vsizes = None, 
     cffs = [1.5],  
     **kwargs,  
):
    """
    This series is especially helpful when selecting slits1.vsize to balance beam flux and energy resolution.
    Moreover, it should be run routinely during commissioning to assess energy resolution and adjust energy calibration if needed.
    
    TODO: fill in more thorough documentation.
    """

    ## Set input variables
    if isinstance(energy_parameters, str):
         energy_parameters = energy_list_parameters[energy_parameters]
    if slit1_vsizes is None:
         slit1_vsizes = [0.01, 0.02, 0.04, 0.1, 0.2, 0.4] 
         """
         ## For more thorough characterization.  Try to run this with carbon_NEXAFS_slow energy parameters.
         slit1_vsizes = np.concatenate((
                np.arange(10, 1, -0.5),
                np.arange(1, 0.1, -0.05), ## Requires gain to be adjusted for SRS570s
                np.arange(0.1, 0.005, -0.005),
        ))
        """
         ### For quicker check


    print("Starting energy resolution series")
    
    ## Start and end at safe configuraiton like WAXSNEXAFS
    yield from load_configuration("DM7NEXAFS")

    ## Set polarization
    yield from set_polarization(90)
    
    ## Open slits 2 and 3, as they are not needed for NEXAFS
    yield from bps.mv(
        slits2.vsize, 10,
        slits2.hsize, 10,
        slits3.vsize, 10,
        slits3.hsize, 10,
        )

    
    ## Load sample at the desired angle
    print("Loading sample: " + str(sample_id))
    yield from load_samp(sample_id)
    yield from rotate_now(20)

    for cff in cffs:
        print("CFF = " + str(cff))
        yield from bps.mv(en.monoen.cff, cff)
        for slit1_vsize in slit1_vsizes:
            print("Slits 1 vsize = " + str(slit1_vsize))
            yield from bps.mv(slits1.vsize, slit1_vsize)
            yield from nbs_energy_scan(
                                        *energy_parameters,
                                        use_2d_detector=False, 
                                        dwell=1,
                                        n_exposures=1, 
                                        group_name="EnergyResolutionSeries",
                                        **kwargs,
                                        )


    ## End in safe/default configuration
    yield from bps.mv(en.monoen.cff, 1.5)
    yield from load_configuration("DM7NEXAFS")



