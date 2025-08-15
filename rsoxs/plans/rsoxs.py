## TODO: would like to change the name of this file to scans.py, but when I change the name and propagate everywhere, I still run into an error ModuleNotFoundError: No module named "rsoxs.plans.rsoxs"

import bluesky.plan_stubs as bps
from bluesky.preprocessors import finalize_wrapper
from functools import partial
from nbs_bl.hw import (
    en,
    shutter_control,
    shutter_open_time,
    sam_X,
    sam_Y,
    waxs_det,
)

from nbs_bl.beamline import GLOBAL_BEAMLINE
from nbs_bl.printing import run_report
from nbs_bl.plans.scans import nbs_count, nbs_gscan, nbs_spiral_square
from nbs_bl.plans.preprocessors import wrap_metadata
from nbs_bl.utils import merge_func
from nbs_bl.queueserver import GLOBAL_USER_STATUS
from nbs_bl.help import (
    _add_to_import_list,
    add_to_plan_list,
    add_to_func_list,
    add_to_plan_list,
    add_to_plan_time_dict,
)
from nbs_bl.plans.scans import nbs_energy_scan

from .per_steps import take_exposure_corrected_reading, one_nd_sticky_exp_step

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

run_report(__file__)

GLOBAL_RSOXS_PLANS = GLOBAL_USER_STATUS.request_status_dict("RSOXS_PLANS", use_redis=True)
GLOBAL_RSOXS_PLANS.clear()


def add_to_rsoxs_list(f, key, **plan_info):
    """
    A function decorator that will add the plan to the built-in list
    """
    _add_to_import_list(f, "rsoxs")
    GLOBAL_RSOXS_PLANS[key] = {}
    GLOBAL_RSOXS_PLANS[key].update(plan_info)
    return f


## Main difference between Bluesky list_scan and scan_nd is that scan_nd has a cycler that can run the scan for all combinations of parameters (e.g., energy, polarization, positions, temperatures).  But for most cases here, it is simpler to use nested for loops, which accomplishes the same purpose.

## count (time) scans.
## Example use:
## RE(nbs_count(num=10, use_2d_detector=False, delay=0, dwell=2)) ## Doesn't take images
## num is number of data points,delay is time between datapoints, dwell is exposure time per point
## RE(nbs_count(num=10, use_2d_detector=True, delay=0, dwell=2)) ## Takes images


## energy scans
## Example use:
## RE(nbs_energy_scan(250, 350, 10, use_2d_detector=False))
## TODO: It is not easy to run a single energy point for multiple exposures because the _make_gscan_points always makes an energy list with length of at least 2.  Main issue is that a time scan's xarray gets organized differently from the energy scan
## TODO: also the energy scans with repeat exposures don't have a time stamp for all repeat exposures, only the first one?


@add_to_plan_list
@merge_func(
    nbs_spiral_square,
    use_func_name=False,
    omit_params=[
        "use_2d_detector",
        "x_motor",
        "y_motor",
        "x_center",
        "y_center",
        "x_range",
        "y_range",
        "x_num",
        "y_num",
    ],
)
def spiral_scan(
    *args, stepsize=0.3, widthX=1.8, widthY=1.8, dwell=1, n_exposures=1, energy=270, polarization=0, **kwargs
):
    """Spiral Scan with motor arguments filled"""
    yield from finalize_wrapper(
        plan=nbs_spiral_square(
            x_motor=sam_X,
            y_motor=sam_Y,
            x_center=sam_X.user_setpoint.get(),
            y_center=sam_Y.user_setpoint.get(),
            x_range=widthX,
            y_range=widthY,
            x_num=round(widthX / stepsize) + 1,
            y_num=round(widthY / stepsize) + 1,
            # per_step = rsoxs_per_step, ## Otherwise complains about multiple values received
            use_2d_detector=True,
            # extra_dets = _extra_dets, ## TODO: probably this line can get deleted since Jamie updated his scans to use_2d_detector?
            energy=energy,
            polarization=polarization,
            **kwargs,
        ),
        final_plan=post_scan_hardware_reset(),
    )


## spiral scans for to find good spot on sample


def post_scan_hardware_reset():
    ## Make sure the shutter is closed, and the scanlock if off after a scan, even if it errors out
    yield from bps.mv(en.scanlock, 0)
    yield from bps.mv(shutter_control, 0)


def _wrap_rsoxs(element, edge):
    def decorator(func):
        return wrap_metadata({"element": element, "edge": edge, "scantype": "rsoxs"})(func)

    return decorator


@add_to_plan_list
@wrap_metadata({"plan_name": "rsoxs", "scantype": "rsoxs"})
@merge_func(nbs_energy_scan, omit_params=["use_2d_detector"])
def rsoxs(*args, **kwargs):
    yield from nbs_energy_scan(*args, use_2d_detector=True, **kwargs)


add_to_plan_time_dict(rsoxs, estimator="gscan_estimate", overhead=1.0)


@add_to_plan_list
@wrap_metadata({"plan_name": "nexafs", "scantype": "nexafs"})
@merge_func(nbs_energy_scan, omit_params=["use_2d_detector"])
def nexafs(*args, **kwargs):
    yield from nbs_energy_scan(*args, use_2d_detector=False, **kwargs)


add_to_plan_time_dict(nexafs, estimator="gscan_estimate", overhead=0.2)


def _rsoxs_factory(energy_grid, element, edge, key):
    @_wrap_rsoxs(element, edge)
    @wrap_metadata({"plan_name": key})
    @merge_func(nbs_energy_scan, omit_params=["use_2d_detector", "start", "stop", "step"])
    def inner(**kwargs):
        yield from nbs_energy_scan(*energy_grid, use_2d_detector=True, **kwargs)

    d = f"Perform an in-place RSoXS scan for {element} with energy pattern {energy_grid} \n"
    inner.__doc__ = d + inner.__doc__

    inner.__qualname__ = key
    inner.__name__ = key
    inner._edge = edge
    inner._short_doc = f"Do RSoXS for {element} from {energy_grid[0]} to {energy_grid[-2]}"
    add_to_plan_time_dict(inner, estimator="gscan_estimate", overhead=1.2, region=energy_grid)

    return inner


@add_to_func_list
def load_rsoxs(filename):
    """
    Load RSoXS plans from a TOML file and inject them into the IPython user namespace.

    Parameters
    ----------
    filename : str
        Path to the TOML file containing XAS plan definitions
    """
    try:
        # Get IPython's user namespace
        ip = get_ipython()
        user_ns = ip.user_ns
    except (NameError, AttributeError):
        # Not running in IPython, just return the generated functions
        user_ns = None

    generated_plans = {}
    with open(filename, "rb") as f:
        regions = tomllib.load(f)
        for _key, value in regions.items():
            if "xas" in _key:
                key = _key.replace("xas", "rsoxs")
            else:
                key = _key
            name = value.get("name", key)
            region = value.get("region")
            element = value.get("element", "")
            edge = value.get("edge", "")
            rsoxs_func = _rsoxs_factory(region, element, edge, key)
            add_to_rsoxs_list(rsoxs_func, key, name=name, element=element, edge=edge, region=region)

            # Store the function
            generated_plans[key] = rsoxs_func

            # If we're in IPython, inject into user namespace
            if user_ns is not None:
                user_ns[key] = rsoxs_func

    # Return the generated plans dictionary in case it's needed
    return generated_plans


## <functionName>? prints out the source code in Bluesky
