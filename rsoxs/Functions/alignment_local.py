
import bluesky.plans as bp
from matplotlib import pyplot as plt
import queue
from PIL import Image
from operator import itemgetter
from copy import deepcopy
import collections
import numpy as np
import orjson
import datetime
import bluesky.plan_stubs as bps
from ophyd import Device
from bluesky.preprocessors import finalize_decorator
from ..redis_config import rsoxs_config #bec, db 
from nbs_bl.hw import(
    sam_viewer,   
    SampleViewer_cam
)
from nbs_bl.printing import run_report
from ..HW.slackbot import rsoxs_bot

from nbs_bl.printing import boxed_text, colored
from .common_functions import args_to_string

def sample_by_value_match(key, string, bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    results = [d for (index, d) in enumerate(bar) if d[key].find(string) >= 0]
    if len(results) == 1:
        return results[0]
    elif len(results) < 1:
        print("No Match")
        return None
    elif len(results) > 1:
        print("More than one result found, returning them all")
        return results


def sample_by_name( name, bar=None):
    return sample_by_value_match("sample_name", name, bar=bar)

def list_samples(bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    text = "  i  Sample Name"
    for index, sample in enumerate(bar):
        text += "\n {} {}".format(index, sample["sample_name"])
        """
        ## PK: commenting this out because I have changed acquisition parameters
        acqs = bar[index]["acquisitions"]
        for acq in acqs:
            text += "\n   {} of {} in {} config, priority {}".format(
                acq["type"],
                acq["edge"],
                acq["configuration"],
                acq["priority"],
            )
        """
    boxed_text("Samples on bar", text, "lightblue", shrink=False)


def sanatize_angle(samp, force=False):
    # translates a requested angle (something in sample['angle']) into an actual angle depending on the kind of sample
    if type(samp["angle"]) == int or type(samp["angle"]) == float:
        goodnumber = True  # make the number fall in the necessary range
    else:
        goodnumber = False  # make all transmission 90 degrees from the back, and all grading 20 deg
    if force and -155 < samp["angle"] < 195:
        samp["bar_loc"]["th"] = samp["angle"]
        return
    if samp["grazing"]:
        # the sample is intended for grazing incidence, so angles should be interpreted to mean
        # 0 - parallel with the face of the sample
        # 90 - normal to the sample
        # 110 - 20 degrees from normal in one direction
        # 70 - 20 degrees from normal in the other direction
        # valid input angles are 0 - 180
        if samp["front"]:
            # sample is on the front of the bar, so valid outputs are between -90 and 90
            if goodnumber:
                samp["bar_loc"]["th"] = float(90 - np.mod(samp["angle"] + 3600, 180))
            else:
                samp["bar_loc"]["th"] = 70  # default grazing incidence samples to 20 degrees incidence angle
                samp["angle"] = 70
                # front grazing sample angle is interpreted as grazing angle
        else:
            if goodnumber:
                angle = float(np.mod(435 - np.mod(-samp["angle"] + 3600, 180), 360) - 165)
                if angle < -155:
                    angle = float(np.mod(435 - np.mod(samp["angle"] + 3600, 180), 360) - 165)
                samp["bar_loc"]["th"] = angle
            else:
                samp["bar_loc"]["th"] = 110
                samp["angle"] = 110
            # back grazing sample angle is interpreted as grazing angle but subtracted from 180
    else:
        if samp["front"]:
            if goodnumber:
                samp["bar_loc"]["th"] = float(np.mod(345 - np.mod(90 + samp["angle"] + 3600, 180) + 90, 360) - 165)
                if samp["bar_loc"]["x0"] > 6 and np.abs(samp["angle"]) > 30:
                    # transmission from the left side of the bar at a incident angle more than 20 degrees,
                    # flip sample around to come from the other side - this can take a minute or two
                    samp["bar_loc"]["th"] = float(
                        np.mod(345 - np.mod(90 - samp["angle"] + 3600, 180) + 90, 360) - 165
                    )
                if samp["bar_loc"]["th"] >= 195:
                    samp["bar_loc"]["th"] = 180
                if samp["bar_loc"]["th"] <= -155:
                    samp["bar_loc"]["th"] = -150
            else:
                samp["bar_loc"]["th"] = 0
                samp["angle"] = 0
        else:
            if goodnumber:
                samp["bar_loc"]["th"] = float(np.mod(90 + samp["angle"] + 3600, 180) - 90)
                if samp["bar_loc"]["x0"] < -5 and np.abs(samp["angle"]) > 30: #TODO figure out the geometry constraints for the back of the bar transmission
                    # transmission from the right side of the bar at a incident angle more than 20 degrees,
                    # flip to come from the left side
                    samp["bar_loc"]["th"] = float(np.mod(90 - samp["angle"] + 3600, 180) - 90.0)
            else:
                samp["bar_loc"]["th"] = 0
                samp["angle"] = 0

    if samp["bar_loc"]["th"] >= 195:
        samp["bar_loc"]["th"] = 195.0
    if samp["bar_loc"]["th"] <= -155:
        samp["bar_loc"]["th"] = -155.0
    


def samp_dict_from_id_or_num(num_or_id):
    if isinstance(num_or_id,str):
        sam_dict = [d for (index, d) in enumerate(rsoxs_config['bar']) if d['sample_id'].find(num_or_id) >= 0]
        if len(sam_dict) > 0:
            sam_dict =  sam_dict[0]
        else:
            raise ValueError(f'sample named {num_or_id} not found')
    else:
        try:
            sam_dict = rsoxs_config['bar'][num_or_id]
        except:
            raise ValueError(f'sample number {num_or_id} not able to be loaded')
    return sam_dict



def offset_bar(xoff, yoff, zoff, thoff, bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    for samp in bar:
        for mot in samp["location"]:
            if mot["motor"] == "x":
                mot["position"] += xoff
            if mot["motor"] == "y":
                mot["position"] += yoff
            if mot["motor"] == "z":
                mot["position"] += zoff
            if mot["motor"] == "th":
                mot["position"] += thoff
        sample_recenter_sample(samp)
    
    
def default_sample(name,
                   #proposal_id,
                   institution='NIST',grazing=False,front=True):
    return {
        "institution": institution,
        "acquisitions": [],
        "components": "",
        "composition": "",
        "bar_loc": {"spot": "0A"},
        "bar_spot": "0A",
        "front": front,
        "grazing": grazing,
        "height": 0.0,
        "angle": 0,
        "density": "",
        "location": [],
        "project_desc": "Calibration",
        "sample_id": name,
        "sample_name": name,
        "sample_desc": '',
        "project_name": "Calibration",
        "notes": "",
        "sample_set": "",
        "sample_state": "",
        #"proposal_id" : proposal_id,
    }
from bluesky.callbacks.mpl_plotting import QtAwareCallback
class BarPlotter(QtAwareCallback):
    def __init__(self, *args, front=None, bar=None, path=None,**kwargs):
        self.path = path
        self.front = front
        self.bar = bar
        super().__init__(*args, **kwargs)

    def stop(self, doc):
        imageuid = doc['run_start']
        images = list(db[imageuid].data("Sample Imager Detector Area Camera_image"))
        image = stitch_sample(images, 25, -6)  # this will start the interactive pointing of samples
        if self.path is not None:
            im = Image.fromarray(image)
            im.save(self.path)
        update_bar(loc_Q, self.front, inbar=self.bar)

import bluesky.preprocessors as bpp
def image_bar( path=None, front=True, bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    global loc_Q
    loc_Q = queue.Queue(1)
    ypos = np.arange(-100, 110, 25)
    
    yield from bp.list_scan([SampleViewer_cam], sam_viewer, ypos)
    """
    yield from bpp.subs_wrapper(
        bp.list_scan([SampleViewer_cam], sam_viewer, ypos),
        #{'stop': [BarPlotter(path=path, front=front, bar=bar)]} ## PK: Using Eliot's code through data security and commenting this out so that it does not attempt to access db.  TODO: rewrite these functions and reorganize into new folder.
    )
    """
    ## Acquisition parameters in Phoebus: ######################
    ## Exposure time = 0.05 s ## Likely the first parameter to be adjusted if image is too bright or dim
    ## Acquire Period: 1 s
    ## Num Images: 1
    ## Exp/Image: 1
    ## Image Mode: Single
    ## Trigger Mode: Fixed Rate
    ## areaDetector Plugins --> Expert (AD detail) --> Prosilica
    ## Binning x = 1, y = 1
    ## Region start x = 0, y = 0
    ## Region size x = 2464, y = 2056
    ## Gain: 0
    ## Data type: UInt8
    ## Color mode: RGB1 ## May need to switch this to something else then back to RGB1 for colors to show up
    ## Bayer convert: None
    ## Shutter mode: None
    ## Wait for plugins: Yes
    ## Image counter: 0
    ## Array callbacks: Enable
    ## Buffer & memory polling: 1
    
    # print('Run locate_samples_from_image() to find your positions interactively')
    # all the rest of this function won't work correctly 
    # because of threading in the run engine, so it needs
    # to be run seperately
    #print(imageuid)

    ## TODO: possibly make a separate RunEngine for taking pictures.  Also update to make it data security compliant.  Possibly run through Jupyter notebook after feeding in spreadsheet and image rather than pointing to db.
    

def locate_samples_from_image( impath, front=True, bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    # if the image was just taken itself, before a bar was compiled, then this can be run to just load that image
    # and then interactively place the elements of bar
    global loc_Q
    # user needs to define the 'bar' in their namespace
    loc_Q = queue.Queue(1)
    if front:
        image = stitch_sample(
            False, False, False, from_image=impath, flip_file=False
        )  # this starts the sample pointing
    else:
        image = stitch_sample(False, False, False, from_image=impath, flip_file=False)
    # stitch samples will be sending signals, update bar will catch those signals and assign the positions to the bar
    update_bar(loc_Q, front,inbar=bar)


def update_bar(loc_Q, front, inbar=None):
    
    """
    updated with whether we are pointing at the front or the back of the bar
    """
    if inbar == None:
        inbar = rsoxs_config['bar']
    from threading import Thread

    global gbar
    gbar = inbar
    try:
        loc_Q.get_nowait()
    except Exception:
        ...

    def worker():
        global gbar
        global sample_image_axes
        samplenum = 0
        lastclicked = 0
        if front:
            # add / replace the front fiducial bar entries (bar[0], bar[-1])
            #AF1 = default_sample("AF1_front",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=True)
            #AF2 = default_sample("AF2_front",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=True)
            #diode = default_sample("diode",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=True)
            AF1 = default_sample("AF1_front",institution=gbar[0]['institution'],front=True)
            AF2 = default_sample("AF2_front",institution=gbar[0]['institution'],front=True)
            diode = default_sample("diode",institution=gbar[0]['institution'],front=True)
            if sample_by_name("AF1_front") is not None:
                gbar.remove(sample_by_name("AF1_front"))
            if sample_by_name("AF2_front") is not None:
                gbar.remove(sample_by_name( "AF2_front"))
            gbar.insert(0, AF1)
            gbar.insert(1, AF2)
            gbar.insert(2, diode)
            ## Appending fiducials/diodes to the end does not always reliably add image position into rsoxs_config (Issue #2, also encountered during 20241006 beam time), so it is simpler to add these at the beginnng.
            
                

        ## TODO: update the back of the bar code if the above front-bar code works
        else:
            # if front fiducials don't exist,add dummy ones (so thge AF2 ones are in the correct position)
            if sample_by_name("AF1_front") is None:
                #AF1 = default_sample("AF1_front",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=True)
                AF1 = default_sample("AF1_front",institution=gbar[0]['institution'],front=True)
                gbar.insert(0, AF1)
            if sample_by_name("AF2_front") is None:
                #AF2 = default_sample("AF2_front",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=True)
                AF2 = default_sample("AF2_front",institution=gbar[0]['institution'],front=True)
                gbar.insert(1, AF2) #gbar.append(AF2)

            # add / replace the back fiducial bar entries (bar[1], bar[-2])

            if sample_by_name("AF1_back") is not None:
                gbar.remove(sample_by_name("AF1_back"))
            if sample_by_name("AF2_back") is not None:
                gbar.remove(sample_by_name("AF2_back"))
            #AF1 = default_sample("AF1_back",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=False)
            #AF2 = default_sample("AF2_back",proposal_id=gbar[0]['proposal_id'],institution=gbar[0]['institution'],front=False)
            AF1 = default_sample("AF1_back",institution=gbar[0]['institution'],front=False)
            AF2 = default_sample("AF2_back",institution=gbar[0]['institution'],front=False)
            gbar.insert(1, AF1)  # inserts in the second position
            gbar.insert(1, AF2) #gbar.insert(-1, AF2)  # inserts in the second to last position
        while True:
            #        for sample in bar:
            sample = gbar[samplenum]
            if sample["front"] != front:  # skip if we are not on the right side of the sample bar
                # (only locate samples that we can see in this image!)
                samplenum += 1
                if samplenum >= len(gbar):
                    print("done")
                    break
                else:
                    continue
            #print(sample)
            print(
                f'\nRight-click on {sample["sample_name"]} location (recorded location is {sample["bar_loc"]["spot"]}).  '
                + "Press n on plot or enter to skip to next sample, p for previous sample, esc to end"
            )
            # ipython input x,y or click in plt which outputs x, y location
            while True:
                try:
                    # print('trying')
                    item = loc_Q.get(timeout=1)
                except Exception:
                    # print('no item')
                    ...
                else:
                    # print('got something')
                    break
            if item != ("enter" or "escape" or "n" or "p") and isinstance(item, list):
                sample["location"] = item
                sample["bar_loc"]["ximg"] = float(item[0]["position"])
                sample["bar_loc"]["yimg"] = float(item[1]["position"])
                if front:
                    sample["bar_loc"]["th0"] = float(0)
                else:
                    sample["bar_loc"]["th0"] = float(180)
                annotateImage(sample_image_axes, item, sample["sample_name"])
                # advance sample and loop
                samplenum += 1
            elif item == "escape":
                print("aborting")
                break
            elif item == "enter" or item == "n":
                print(f'leaving this {sample["sample_name"]} unchanged')
                samplenum += 1
            elif item == "p":
                print("Previous sample")
                samplenum -= 1
            if samplenum >= len(gbar):
                print("done")
                break

    t = Thread(target=worker)
    t.start()


def annotateImage(axes, item, name):
    ycoord = item[0]["position"]
    xcoord = item[1]["position"]

    a = axes.annotate(
        name,
        xy=(xcoord, ycoord),
        xycoords="data",
        xytext=(xcoord - 3, ycoord + 10),
        textcoords="data",
        arrowprops=dict(color="red", arrowstyle="->"),
        horizontalalignment="center",
        verticalalignment="bottom",
        color="red",
    )

    a.draggable()
    plt.draw()


def stitch_sample(images, step_size, y_off, from_image=None, flip_file=False):
    global sample_image_axes

    if isinstance(from_image, str):
        im_frame = Image.open(from_image)
        result = np.array(im_frame)
        if flip_file:
            result = np.flipud(result)
    else:
        pixel_step = int(step_size * (1760) / 25)
        pixel_overlap = 2464 - pixel_step
        result = images[0][0]
        i = 0
        for imageb in images[1:]:
            image = imageb[0]
            i += 1
            if y_off > 0:
                result = np.concatenate((image[(y_off * i) :, :], result[:-(y_off), pixel_overlap:]), axis=1)
            elif y_off < 0:
                result = np.concatenate((image[: (y_off * i), :], result[-(y_off):, pixel_overlap:]), axis=1)
            else:
                result = np.concatenate((image[:, :], result[:, pixel_overlap:]), axis=1)
        # result = np.flipud(result)

    fig, ax = plt.subplots()
    ax.imshow(result, extent=[-210, 25, -14.5, 14.5])
    sample_image_axes = ax
    fig.canvas.mpl_connect("button_press_event", plot_click)
    fig.canvas.mpl_connect("key_press_event", plot_key_press)
    plt.show()
    return result


def print_click(event):
    # print(event.xdata, event.ydata)
    global gbar, barloc
    item = []
    item.append({"motor": "x", "position": float(event.ydata)})
    item.append({"motor": "y", "position": float(event.xdata)})
    item.append({"motor": "z", "position": 0.0})
    item.append({"motor": "th", "position": 180.0})
    gbar[barloc]["location"] = item
    print(f"Setting location {barloc} on bar to clicked position")


def plot_click(event):
    # print(event.xdata, event.ydata)
    global loc_Q
    item = []
    item.append({"motor": "x", "position": float(event.ydata), "order": 0})
    item.append({"motor": "y", "position": float(event.xdata), "order": 0})
    item.append({"motor": "z", "position": 0.0, "order": 0})
    item.append({"motor": "th", "position": 180.0, "order": 0})
    if not loc_Q.full() and event.button == 3:
        loc_Q.put(item, block=False)


def plot_key_press(event):
    global loc_Q
    if not loc_Q.full() and (
        event.key == "enter" or event.key == "escape" or event.key == "n" or event.key == "p"
    ):
        loc_Q.put(event.key, block=False)


def offset_bar( xoff, yoff, zoff, thoff, bar = None):
    
    if bar == None:
        bar = rsoxs_config['bar']
    for samp in bar:
        for mot in samp["location"]:
            if mot["motor"] == "x":
                mot["position"] += xoff
            if mot["motor"] == "y":
                mot["position"] += yoff
            if mot["motor"] == "z":
                mot["position"] += zoff
            if mot["motor"] == "th":
                mot["position"] += thoff
    

def correct_bar(fiduciallist, include_back, training_wheels=True, bar = None):
    """
    originally this function adjusted the x, y, positions of samples on a bar
    to align with the x-y locations found by fiducials
    now the fiducial needs 4 x measurements at the different angles, (-90,0.90,180)
    and the one measurement of y for each fiducial
    and the sample z offset can be found as well
    so apritrary angles can be gone to if requested (this should be recorded in the 'th' parameter in bar_loc

    fiducial list is the list output by find_fiducials()
    """
    if bar == None:
        bar = deepcopy(rsoxs_config['bar'])
    af2y = fiduciallist[0]
    af2xm90 = fiduciallist[1]
    af2x0 = fiduciallist[2]
    af2x90 = fiduciallist[3]
    af2x180 = fiduciallist[4]
    af1y = fiduciallist[5]
    af1xm90 = fiduciallist[6]
    af1x0 = fiduciallist[7]
    af1x90 = fiduciallist[8]
    af1x180 = fiduciallist[9]
    af1_front = sample_by_name("AF1_front")
    af2_front = sample_by_name("AF2_front")
    af1_back = sample_by_name("AF1_back")
    af2_back = sample_by_name("AF2_back")
    if af1_back is None:
        back = False
    else:
        back = include_back
    af1x_img = af1_front["location"][0]["position"] # TODO: should change to image position, so you can run fiducials again and again without problems
    af1y_img = af1_front["location"][1]["position"]
    af2x_img = af2_front["location"][0]["position"]
    af2y_img = af2_front["location"][1]["position"]
    # adding the possibility of a back fiducial position as well as front
    # these will be nonsense if there was no back image (image bar didn't add in these positions)
    # but they won't be used, unless a sample is marked as being on the back
    if back:
        af1xback_img = af1_back["location"][0]["position"]
        af1yback_img = af1_back["location"][1]["position"]
        af2xback_img = af2_back["location"][0]["position"]
        af2yback_img = af2_back["location"][1]["position"]

    af1x, af1zoff, af1xoff = af_rotation(
        af1xm90, af1x0, af1x90, af1x180
    )  # find the center of rotation from fiducials
    af2x, af2zoff, af2xoff = af_rotation(af2xm90, af2x0, af2x90, af2x180)
    # these values are the corresponding values at theta=0,
    # which is what we want if the image is of the front of the bar
    af1xback = rotatedx(af1x, 180, af1zoff, af1xoff)
    af2xback = rotatedx(af2x, 180, af2zoff, af2xoff)
    # if we are looking at the sample from the back,
    # then we need to rotate the fiducial x and y location for the sample corrections

    x_offset = af1x - af1x_img  # offset from X-rays to image in x
    y_offset = af1y - af1y_img  # offset from X-rays to image in y
    y_image_offset = af1y_img - af2y_img  # distance between fiducial y positions (should be ~ -190)
    if back:
        x_offset_back = af1xback - af1xback_img  # offset from X-rays to image in x on the back
        y_offset_back = af1y - af1yback_img  # offset from X-rays to image in x
        y_image_offset_back = (
            af1yback_img - af2yback_img
        )  # distance between fiducial y positions (should be ~ -190)

    if training_wheels:
        assert abs(abs(af2y - af1y) - abs(y_image_offset)) < 5, (
            "Hmm... "
            "it seems like the length of the bar has changed by more than"
            " 5 mm between the imager and the chamber.  \n \n Are you sure"
            " your alignment fiducials are correctly located?  \n\n If you're"
            " really sure, rerun with training_wheels=false."
        )

    dx = af2x - af2x_img - x_offset  # offset of Af2 X-rays to image in x relative to Af1 (mostly rotating)
    # dx is the total offset needed for a position in the image to be located with X-rays at the bottom of the bar
    # the
    dy = af2y - af2y_img - y_offset  # offset of Af2 X-rays to image in y relative to Af1 (mostly stretching)
    if back:
        dxb = (
            af2xback - af1xback + af1xback_img - af2xback_img
        )  # offset of Af2 X-rays to image in x relative to Af1 (mostly rotating)
        # offset from the top of the bar to the bottom of the bar with X-rays  minus
        # offset of the top of the bar to the bottom in the image
        # dxb is the extra bit needed to move the bottom of the bar to correct for this rotation
        dyb = (af2y - af1y) - (
            af2yback_img - af1yback_img
        )  # offset of Af2 X-rays to image in y relative to Af1 (this is scaling the image - should be 0)
        # dyb is the extra bit needed to scale the bottom of the bar to correct for this scaling
    # dx, dy, dyb, and dxb are all relative correction factors, which are from the top of the bar to the bottom,
    # we use run_y to translate this to a offset per mm
    run_y = af2y - af1y  # (distance between the fiducial markers) (above are the total delta over this run,
    # in between this will be scaled

    for samp in bar:
        xpos = samp["bar_loc"]["ximg"]  # x position from the image
        ypos = samp["bar_loc"]["yimg"]  # y position from the image
        xoff = af1xoff - (af1xoff - af2xoff) * (ypos - af1y) / run_y
        samp["bar_loc"]["xoff"] = float(xoff)  # this should pretty much be the same for both fiducials,
        # but just in case there is a tilt,
        # we account for that here, taking af1soff if the sample is towards the top and af2soff as it is lower

        if samp["front"]:
            newx = xpos + x_offset + (ypos - af1y) * dx / run_y
            # new position is the image position, plus the offset from the image to the x-rays, plus a linear correction
            # from the top of the bar to the bottom
            newy = ypos + y_offset + (ypos - af1y) * dy / run_y
            samp["bar_loc"]["x0"] = float(
                newx
            )  # these are the positions at 0 rotation, so for the front, we are already good
        elif back:
            newx = xpos + x_offset_back + (ypos - af1y) * dxb / run_y
            newy = ypos + y_offset_back + (ypos - af1y) * dyb / run_y
            samp["bar_loc"]["x0"] = float(2 * xoff - newx)  # these are the positions at 0 rotation,
            # so for the back, we have to correct
        else:
            continue  # sample is on the back, and we are not doing the back of the bar, so skip
        samp["bar_loc"]["y0"] = float(newy)
        # recording of fiducial information as well with every sample, so they will know how to rotate
        samp["bar_loc"]["af1y"] = float(af1y)
        samp["bar_loc"]["af2y"] = float(af2y)
        samp["bar_loc"]["af1xoff"] = float(af1xoff)
        samp["bar_loc"]["af2xoff"] = float(af2xoff)
        samp["bar_loc"]["af1zoff"] = float(af1zoff)
        samp["bar_loc"]["af2zoff"] = float(af2zoff)

        zoff = zoffset(
            af1zoff,
            af2zoff,
            newy,
            front=samp["front"],
            height=samp["height"],
            af1y=af1y,
            af2y=af2y,
        )
        samp["bar_loc"]["zoff"] = float(zoff)

        # now we can rotate the sample to the desired position (in the 'angle' metadata)
        # moving z is dangerous = best to keep it at 0 by default
        rotate_sample(samp)  # this will take the positions found above and the desired incident angle and
        # rotate the location of the sample accordingly
    rsoxs_config['bar'] = bar #event_model.sanitize_doc() #rsoxs_config['bar'] = orjson.dumps(bar)
    
def zoffset(af1zoff, af2zoff, y, front=True, height=0.25, af1y=-186.3, af2y=4):
    """
    Using the z offset of the fiducial positions from the center of rotation,
    project the z offset of the surface of a given sample at some y position between
    the fiducials.
    """

    m = (af2zoff - af1zoff) / (af2y - af1y)  # slope of bar
    z0 = af1zoff + m * (y - af1y)

    # offset the line by the front/back offset + height
    if front:
        #return z0 - 2.5 - height # 
        return z0 + 4.5 - height # fixed Nov 2023 with new rotation stage
    else:
        return z0 + height
    # return the offset intersect


def rotatedx(x0, theta, zoff, xoff=1.88, thoff=0):
    """
    given the x position at 0 rotation (from the image of the sample bar)
    and a rotation angle, the offset of rotation in z and x (as well as a potential theta offset)
    find the correct x position to move to at a different rotation angle
    """
    return (
        xoff + (x0 - xoff) * np.cos((theta - thoff) * np.pi / 180) - zoff * np.sin((theta - thoff) * np.pi / 180)
    )


def rotatedz(x0, theta, zoff, xoff=1.88, thoff=0):
    """
    given the x position at 0 rotation (from the image of the sample bar)
    and a rotation angle, the offset of rotation in z and x axes (as well as a potential theta offset)
    find the correct z position to move to to keep a particular sample at the same intersection point with X-rays
    """
    return (
        zoff + (x0 - xoff) * np.sin((theta - thoff) * np.pi / 180) - zoff * np.cos((theta - thoff) * np.pi / 180)
    )


def af_rotation(xfm90, xf0, xf90, xf180):
    """
    takes the fiducial centers measured in the x direction at -90, 0, 90, and 180 degrees
    and returns the offset in x and z from the center of rotation, as well as the
    unrotated x positon of the fiducial marker.

    the x offset is not expected to vary between loads, and has been measured to be 1.88,
    while the z offset is as the bar flexes in this direction, and will be used to
    map the surface locations of other samples between the fiducials

    """

    x0 = xf0
    xoff = (xf180 + x0) / 2
    zoff = (xfm90 - xf90) / 2
    return (x0, zoff, xoff)



def rotate_sample(samp, force=False):
    """
    rotate a sample position to the requested theta position
    the requested sample position is set in the angle metadata (sample['angle'])
    """
    sanatize_angle(samp, force)  # makes sure the requested angle is translated into a real angle for acquisition
    theta_new = samp["bar_loc"]["th"]
    x0 = samp["bar_loc"]["x0"]
    y0 = samp["bar_loc"]["y0"]
    xoff = samp["bar_loc"]["xoff"]
    zoff = samp["bar_loc"]["zoff"]

    newx = rotatedx(x0, theta_new, zoff, xoff=xoff)
    for motor in samp["location"]:
        if motor["motor"] == "x":
            motor["position"] = newx
        if motor["motor"] == "th":
            motor["position"] = theta_new
        if motor["motor"] == "y":
            motor["position"] = y0
    # in future, updating y (if the rotation axis is not perfectly along y
    # and z (to keep the sample-detector distance constant) as needed would be good as well
    # newz = rotatedz(newx, th, zoff, af1xoff)


def sample_recenter_sample(samp):
    # the current samp['location'] is correct, the point of this is to make sure the x0 and y0 and incident angles
    # are updated accordingly, because the samp['location'] will generally be recalculated and overwritten next time
    # a sample rotation is requested
    # assume the center of rotation for the sample is already calculated correctly (otherwise correct bar is needed)
    # first record the location
    for loc in samp["location"]:
        if loc["motor"] == "x":
            newrotatedx = loc["position"]
        if loc["motor"] == "y":
            newy = loc["position"]
        if loc["motor"] == "th":
            newangle = loc["position"]
    # get the rotation parameters from the metadata
    xoff = samp["bar_loc"]["xoff"]
    zoff = samp["bar_loc"]["zoff"]
    # find the x0 location which would result in this new position
    newx0 = rotatedx(newrotatedx, -newangle, zoff, xoff=xoff)  # we rotate by the negative angle to get back to x0
    samp["bar_loc"]["x0"] = newx0
    samp["bar_loc"]["y0"] = newy  # y and y0 are the same, so we can just copy this
    samp["angle"] = newangle
    


def read_positions(bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    # for when the positions are altered by hand in the excel sheet, (i.e. after spiral scans)
    # this reads those positions and sets the default positions (x0 and y0) to match
    for samp in bar:
        sample_recenter_sample(samp)


def resolve_spirals(bar=None):
    if bar == None:
        bar = rsoxs_config['bar']
    for samp in bar:
        if len(str(samp['bar_loc'].get('spiral_started',''))) > 0 and len(samp['bar_loc'].get('spiral_done','')) == 0:
            h = db.v2[samp['bar_loc']['spiral_started']]
            ys = h['primary']['data']['RSoXS Sample Up-Down'].read()
            xs = h['primary']['data']['RSoXS Sample Outboard-Inboard'].read()
            th = h['baseline']['data']['RSoXS Sample Rotation'][0]#th = h['baseline']['data']['RSoXS Sample Rotation'].read()[0]
            z = h['baseline']['data']['RSoXS Sample Downstream-Upstream'][0]#z = h['baseline']['data']['RSoXS Sample Downstream-Upstream'].read()[0]
            #xs = np.array(list(h.data('RSoXS Sample Outboard-Inboard')))
            #th = np.array(list(h.data('RSoXS Sample Rotation','baseline')))[0]
            #z = np.array(list(h.data('RSoXS Sample Downstream-Upstream','baseline')))[0]
            if len(ys) == len(xs) and len(ys > 0):
                im_num = input(f"sample {samp['sample_name']} scan {h.start['scan_id']} which image number (or numbers, seperated by commas) is/are best?  ")
                for i,im in enumerate(im_num.split(",")):
                    im = int(im)
                    if i>0:
                        accept = input(f"duplicate {samp['sample_name']} to a new sample with position {im} at ({xs[im],ys[im]}) (y,n)?")
                        if accept in ['y','Y','yes']:
                            newsamp =deepcopy(samp)
                            newsamp['location'] = [{'motor':'x','position':xs[im]},
                                                {'motor':'y','position':ys[im]},
                                                {'motor':'th','position':th},
                                                {'motor':'z','position':z}]
                            newsamp['bar_loc']['spiral_done']={"scan":h.start['uid'],
                                                'best_num':im}
                            newsamp['sample_name']+=f'_{i}'
                            newsamp['sample_id']+=f'_{i}'
                            bar.append(newsamp)
                    else:
                        accept = input(f"image {im} at ({xs[im],ys[im]}) is correct (y,n)?")
                        if accept in ['y','Y','yes']:
                            samp['location'] = [{'motor':'x','position':xs[im]},
                                                {'motor':'y','position':ys[im]},
                                                {'motor':'th','position':th},
                                                {'motor':'z','position':z}]
                            samp['bar_loc']['spiral_done']={"scan":h.start['uid'],
                                                'best_num':im}
                            



def acq(id_or_num,acq_num=0):
    samp = samp_dict_from_id_or_num(id_or_num)
    if len(samp['acquisitions']) >= acq_num:
        return samp['acquisitions'][acq_num]
    else:
        print(f'sample {samp["sample_name"]} does not have an acquisition #f{acq_num}')
        return {}
