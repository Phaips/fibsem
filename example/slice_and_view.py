# slice and view


from ctypes import alignment
import os
import logging
from pprint import pprint

import fibsem
from fibsem import acquire, milling, utils, alignment
from fibsem.structures import ImageSettings, MillingSettings

import napari
import zarr 


def main():

    PROTOCOL_PATH = os.path.join(os.path.dirname(__file__), "protocol_slice_and_view.yaml")
    microscope, settings = utils.setup_session(protocol_path = PROTOCOL_PATH)

    # setup for milling
    milling.setup_milling(microscope, settings.system.application_file)

    # # setup napari viewer
    # viewer = napari.Viewer()
    # viewer.add_image(eb_image.data, name="eb_image", colormap="gray")
    # viewer.add_image(ib_image.data, name="eb_image", colormap="gray")

    settings.image.label = "reference"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)

    # TODO: persistent zarr?
    # ebz: zarr.Array = zarr.array(eb_image.data)
    # ibz: zarr.Array = zarr.array(ib_image.data) 


    for slice_idx in range(settings.protocol["steps"]):

        # slice
        logging.info("------------------------ SLICE ------------------------")
        milling_settings = MillingSettings.__from_dict__(settings.protocol["milling"])       
        patterns = milling._draw_rectangle_pattern_v2(microscope, milling_settings)
        estimated_milling_time = milling.estimate_milling_time_in_seconds([patterns])
        logging.info(f"Estimated milling time: {estimated_milling_time}")
        milling.run_milling(microscope, milling_current=milling_settings.milling_current)


        milling.finish_milling(microscope, settings.default.imaging_current) # dont think this is required.

        # view
        logging.info("------------------------ VIEW ------------------------")
        settings.image.label = f"slice_{slice_idx}"
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)

        # visualise
        # ebz.append(eb_image.data)
        # ibz.append(ib_image.data)

        # move?

        # align?
        # alignment.align_using_reference_images(microscope, settings, ref_image, eb_image)


    

if __name__ == "__main__":
    main()
