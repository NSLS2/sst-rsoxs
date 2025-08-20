import numpy as np
import xarray as xr
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm ## For log scaling in imshow
import hvplot.xarray



def viewAllSpiralImages(
    scan,
    format = "matplotlib", 
    logScale = True, 
    contrastLimits = [1, 1e5],
    limitsInboardOutboardDownUp = [0, 61.7, 0, 61.4],
    ):

    """
    View spiral images arranged according to their spatial location on the sample.  Note that the sample faces downstream, and the arrangement represents the directions on the back of the sample bar.

    Args:
        scan: xarray.dataarray
            Scan data that has been formatted using PyHyperScattering.
        format: string
            Choose from the following options:
                "matplotlib": (default) Plots a static plot using matplotlib tools.  Useful to obtain formatted images that can be used in slides or publications.
                "hvplot": Plots interactive plot that can be zoomed using scrolling.
        logScale: boolean
            True: (default) Images are plotted in log scale
            False: Images are plotted in linear scale
        contrastLimits: list of length 2, contains float values
            Enter the lower and upper bounds to define the range of intensities that are shown.
        limitsInboardOutboardDownUp: list of length 4, contains float values
            For format="matplotlib" cases, this list contains the [outboard, inboard, down, up] bounds in mm for plotting each image.
            Default value represents the width (61.7 mm) and height (61.4 mm) of the Greateyes CCD sensor.

    Returns: 
        Grid plot of spiral images.

    Raises:

    Examples:
    """

    ## TODO: put in ability to pick and view a single image or a few images.  Maybe it should be its own function and can be generalized for any scans, not just spirals.
    ## Should take in list of indices for the spot numbers and then plot those images.
    ## loadRun with dims = "time" and then use the attrs to get the coordinates
    
    xMotorPositions = scan.attrs["sam_x"]
    yMotorPositions = scan.attrs["sam_y"]
    timestamps = scan.attrs["time"]

    if format == "matplotlib":
        numberRows, numberColumns = len(scan["sam_y"]), len(scan["sam_x"])
        fig, axs = plt.subplots(numberRows, numberColumns, figsize=(numberColumns*3.25, numberRows*3.25), edgecolor=(0, 0, 0, 0), linewidth=3); #figsize=(3.25, 3.25) for figure
        #fig.suptitle((""), color=(0, 0, 0, 1), fontname="Calibri", size=24)
        ## Enxure axs always stays a 2D array
        if numberRows == 1 and numberColumns == 1: axs = np.array([[axs]])
        if numberRows == 1 and numberColumns > 1: axs = axs.reshape(1, numberColumns)
        if numberRows > 1 and numberColumns == 1: axs = axs.reshape(numberRows, 1)


        for indexPlotRow, yMotorPosition in enumerate(scan["sam_y"]):
            for indexPlotColumn, xMotorPosition in enumerate(scan["sam_x"]):
                image = scan.sel(sam_y=yMotorPosition, sam_x=xMotorPosition, method="nearest")

                ## Identify index number of image in order of time
                for indexImage, timestamp in enumerate(timestamps):
                    if xMotorPositions[indexImage] == xMotorPosition and yMotorPositions[indexImage] == yMotorPosition: break

                ## Plot
                ax = axs[indexPlotRow, indexPlotColumn]
                ax.set_title(("Image " + str(indexImage) + ", x = " + str(float(xMotorPosition)) + ", y = " + str(float(yMotorPosition))), color=(0, 0, 0, 1), size=12)
                if logScale: ax.imshow(image, extent=[limitsInboardOutboardDownUp[0], limitsInboardOutboardDownUp[1], limitsInboardOutboardDownUp[3], limitsInboardOutboardDownUp[2]], cmap=matplotlib.colormaps['RdYlBu_r'], norm=LogNorm(vmin=contrastLimits[0], vmax=contrastLimits[1])) ## If needed, a pedestal could be added for better viewing of log-scale images
                else: ax.imshow(image, extent=[limitsInboardOutboardDownUp[0], limitsInboardOutboardDownUp[1], limitsInboardOutboardDownUp[3], limitsInboardOutboardDownUp[2]], cmap=matplotlib.colormaps['RdYlBu_r'], vmin=contrastLimits[0], vmax=contrastLimits[1])
                
        ## Plot Formatting
        for indexRow in np.arange(0, numberRows, 1):
            for indexColumn in np.arange(0, numberColumns, 1):
                ax = axs[indexRow, indexColumn]
                ## Subplot and axes labels
                ax.set_xlabel("Outboard-inboard (mm)", color=(0, 0, 0, 1), size=12)
                ax.set_ylabel("Down-up (mm)", color=(0, 0, 0, 1), size=12)
                ## Axes scaling and ranges
                ax.set_xscale("linear")
                ax.set_yscale("linear")
                ax.set_xlim([limitsInboardOutboardDownUp[0], limitsInboardOutboardDownUp[1]])
                ax.set_ylim([limitsInboardOutboardDownUp[2], limitsInboardOutboardDownUp[3]])
                ## Border formatting
                for Border in np.array(["top", "bottom", "left", "right"]):
                    ax.spines[Border].set_linewidth(2) ## axes/border linewidths
                    ax.spines[Border].set_color((0, 0, 0, 1)) ## axes/border colors
                for Axis in np.array(["x", "y"]): ax.tick_params(axis=Axis,colors=(0, 0, 0, 1), width=2)
        plt.tight_layout() ## Ensures that subplots don't overlap
        plt.show()


    if format == "hvplot":
        ## TODO: needs testing and formatting
        scan.hvplot(x='pix_x', y='pix_y', row='sam_x', col='sam_y',colorbar=False,cmap="Terrain",logz=logScale,clim=(contrastLimits[0],contrastLimits[1]))
