import numpy as np
import bluesky.plan_stubs as bps
from nbs_bl.hw import (
    en,
    grating,
    mirror2,
    Sample_TEY_int,
)
from nbs_bl.gGrEqns import get_mirror_grating_angles, find_best_offsets
from nbs_bl.plans.scans import nbs_list_scan
from .fly_alignment import rsoxs_fly_max
from ..Functions.alignment import load_samp, rotate_now



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
    # RE(load_sample(sample_by_name(bar, 'HOPG')))
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






def scan_pgm_angles(
    lines_per_mm_pgm = 250,
    polarizations = [90, 90, 90, 90, 90], #polarizations = np.full(shape = 5, fill_value = 90),
    energies = [291.65, 291.65, 291.65, 291.65, 291.65], #energies = np.full(shape = 5, fill_value = 291.65),
    cffs = [1.35, 1.4, 1.45, 1.5, 1.55],
    diffraction_orders = [1, 1, 1, 1, 1], #diffraction_orders = np.full(shape = 5, fill_value = 1),
    sample_ids = ["HOPG", "HOPG", "HOPG", "HOPG", "HOPG"], #sample_ids = np.full(5, "HOPG"),
    sample_angles = [20, 20, 20, 20, 20],#sample_angles = np.full(shape = 5, fill_value = 20),
    radius_search_window = 0.8,
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
