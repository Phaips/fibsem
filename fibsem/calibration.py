
import logging
from datetime import datetime

import numpy as np
from autoscript_sdb_microscope_client import SdbMicroscopeClient
from autoscript_sdb_microscope_client.enumerations import CoordinateSystem, ManipulatorCoordinateSystem
from autoscript_sdb_microscope_client.structures import StagePosition

from fibsem import acquire, movement
from fibsem.structures import (BeamSettings, MicroscopeState, BeamType, ImageSettings, MicroscopeSettings)

from pathlib import Path

def auto_link_stage(microscope: SdbMicroscopeClient, hfw: float = 150e-6) -> None:
    """Automatically focus and link sample stage z-height.

    Notes:
        - Focusing determines the working distance (focal distance) of the beam
        - Relinking is required whenever there is a significant change in vertical distance, i.e. moving
          from the landing grid to the sample grid.
        - Linking determines the specimen coordinate system, as it is defined as the relative dimensions of the top of stage
          to the instruments.
    """

    microscope.imaging.set_active_view(BeamType.ELECTRON.value)
    original_hfw = microscope.beams.electron_beam.horizontal_field_width.value
    microscope.beams.electron_beam.horizontal_field_width.value = hfw
    acquire.autocontrast(microscope, beam_type=BeamType.ELECTRON)
    microscope.auto_functions.run_auto_focus()
    microscope.specimen.stage.link()
    # NOTE: replace with auto_focus_and_link if performance of focus is poor
    # # Restore original settings
    microscope.beams.electron_beam.horizontal_field_width.value = original_hfw

def auto_discharge_beam(microscope: SdbMicroscopeClient, image_settings: ImageSettings, n_iterations: int = 10):

    # take sequence of 5 images quickly,
    resolution = image_settings.resolution
    dwell_time = image_settings.dwell_time
    autocontrast = image_settings.autocontrast
    beam_type = image_settings.beam_type
    
    image_settings.beam_type = BeamType.ELECTRON
    image_settings.resolution = "768x512"
    image_settings.dwell_time = 200e-9
    image_settings.autocontrast = False
    
    logging.info(f"Bring me Thanos!") # important information
     
    for i in range(n_iterations):
        acquire.new_image(microscope, image_settings)

    # autocontrast
    acquire.autocontrast(microscope, BeamType.ELECTRON)

    # take image
    image_settings.resolution = resolution
    image_settings.dwell_time = dwell_time
    image_settings.autocontrast = autocontrast
    acquire.new_image(microscope, image_settings)
    
    image_settings.beam_type = beam_type

def auto_needle_calibration(microscope: SdbMicroscopeClient, settings: MicroscopeSettings):

    settings.image.hfw = 900e-6
    acquire.take_reference_images(microscope, settings.image)

    # TODO: move stage out of the way
    movement.move_needle_to_position_offset(microscope)    

    # focus on the needle
    acquire.autocontrast(microscope, BeamType.ELECTRON)
    microscope.auto_functions.run_auto_focus()
    acquire.take_reference_images(microscope, settings.image)

    # set coordinate system
    microscope.specimen.manipulator.set_default_coordinate_system(ManipulatorCoordinateSystem.STAGE)
    
    # low res alignment
    align_needle_to_eucentric_position(microscope, settings, path=None, validate=False)

    # focus on needle
    acquire.autocontrast(microscope, BeamType.ELECTRON)
    microscope.auto_functions.run_auto_focus()
    acquire.take_reference_images(microscope, settings.image)

    # medium res alignment
    settings.image.hfw=400e-6
    align_needle_to_eucentric_position(microscope, settings, path=None, validate=False)

    # high res alignment
    settings.image.hfw=150e-6
    align_needle_to_eucentric_position(microscope, settings, path=None, validate=False)

    logging.info(f"Finished automatic needle calibration.")


def align_needle_to_eucentric_position(
    microscope: SdbMicroscopeClient,
    settings: MicroscopeSettings,
    path: Path = None,
    validate: bool = False,
) -> None:
    """Move the needle to the eucentric position, and save the updated position to disk

    Args:
        microscope (SdbMicroscopeClient): autoscript microscope instance
        settings (MicroscopeSettings): microscope settings
        lamella (Lamella): current lamella
    """

    from fibsem.ui import windows as fibsem_ui_windows
    from fibsem.detection.utils import DetectionType, DetectionFeature
    from fibsem import utils

    # TODO: remove ui elements from this function... just use base detect_features

    # take reference images
    settings.image.save = False
    settings.image.beam_type = BeamType.ELECTRON
    ref_eb = acquire.new_image(microscope=microscope, settings=settings.image)

    det = fibsem_ui_windows.detect_features(
        microscope=microscope,
        settings=settings,
        ref_image=ref_eb,
        features=[
            DetectionFeature(DetectionType.NeedleTip, None),
            DetectionFeature(DetectionType.ImageCentre, None),
        ],
        validate=validate,
    )

    movement.move_needle_relative_with_corrected_movement(
        microscope=microscope,
        dx=det.distance_metres.x,
        dy=det.distance_metres.y,
        beam_type=BeamType.ELECTRON,
    )

    # take reference images
    settings.image.save = False
    settings.image.beam_type = BeamType.ION
    ref_ib = acquire.new_image(microscope=microscope, settings=settings.image)

    det = fibsem_ui_windows.detect_features(
        microscope=microscope,
        settings=settings,
        ref_image=ref_ib,
        features=[
            DetectionFeature(DetectionType.NeedleTip, None),
            DetectionFeature(DetectionType.ImageCentre, None),
        ],
        validate=validate,
    )

    movement.move_needle_relative_with_corrected_movement(
        microscope=microscope, dx=0, dy=-det.distance_metres.y, beam_type=BeamType.ION,
    )

    # take image
    acquire.take_reference_images(microscope, settings.image)

    if path is not None:
        # save the updated position to disk
        utils.save_needle_yaml(
            path, microscope.specimen.manipulator.current_position
        )

def auto_home_and_link(microscope: SdbMicroscopeClient, state: MicroscopeState) -> None:

    # home the stage
    logging.info(f"Homing stage...")
    microscope.specimen.stage.home()

    # move to saved eucentric state
    set_microscope_state(microscope, state)

    # set the working distances to 3.91mm, 16.5mm
    microscope.beams.electron_beam.working_distance.value = 3.91e-3 # MAGIC_NUMBER
    microscope.beams.ion_beam.working_distance.value = 16.5e-3      # MAGIC_NUMBER

    # link
    logging.info("Linking stage...")
    microscope.specimen.stage.link()


# STATE MANAGEMENT

def get_raw_stage_position(microscope: SdbMicroscopeClient) -> StagePosition:
    """Get the current stage position in raw coordinate system, and switch back to specimen"""
    microscope.specimen.stage.set_default_coordinate_system(CoordinateSystem.RAW)
    stage_position = microscope.specimen.stage.current_position
    microscope.specimen.stage.set_default_coordinate_system(CoordinateSystem.SPECIMEN)

    return stage_position

def get_current_microscope_state(
    microscope: SdbMicroscopeClient
) -> MicroscopeState:
    """Get the current microscope state v2 """

    current_microscope_state = MicroscopeState(
        timestamp=datetime.timestamp(datetime.now()),
        # get absolute stage coordinates (RAW)
        absolute_position=get_raw_stage_position(microscope),
        # electron beam settings
        eb_settings=BeamSettings(
            beam_type=BeamType.ELECTRON,
            working_distance=microscope.beams.electron_beam.working_distance.value,
            beam_current=microscope.beams.electron_beam.beam_current.value,
            hfw=microscope.beams.electron_beam.horizontal_field_width.value,
            resolution=microscope.beams.electron_beam.scanning.resolution.value,
            dwell_time=microscope.beams.electron_beam.scanning.dwell_time.value,
        ),
        # ion beam settings
        ib_settings=BeamSettings(
            beam_type=BeamType.ION,
            working_distance=microscope.beams.ion_beam.working_distance.value,
            beam_current=microscope.beams.ion_beam.beam_current.value,
            hfw=microscope.beams.ion_beam.horizontal_field_width.value,
            resolution=microscope.beams.ion_beam.scanning.resolution.value,
            dwell_time=microscope.beams.ion_beam.scanning.dwell_time.value,
        ),
    )

    return current_microscope_state


def set_microscope_state(microscope: SdbMicroscopeClient, microscope_state: MicroscopeState):
    """Reset the microscope state to the provided state"""

    logging.info(
        f"restoring microscope state..."
    )

    # move to position
    movement.safe_absolute_stage_movement(
        microscope=microscope, stage_position=microscope_state.absolute_position
    )

    # restore electron beam
    logging.info(f"restoring electron beam settings...")
    microscope.beams.electron_beam.working_distance.value = (
        microscope_state.eb_settings.working_distance
    )
    microscope.beams.electron_beam.beam_current.value = (
        microscope_state.eb_settings.beam_current
    )
    microscope.beams.electron_beam.horizontal_field_width.value = (
        microscope_state.eb_settings.hfw
    )
    microscope.beams.electron_beam.scanning.resolution.value = (
        microscope_state.eb_settings.resolution
    )
    microscope.beams.electron_beam.scanning.dwell_time.value = (
        microscope_state.eb_settings.dwell_time
    )
    # microscope.beams.electron_beam.stigmator.value = (
    #     microscope_state.eb_settings.stigmation
    # )

    # restore ion beam
    logging.info(f"restoring ion beam settings...")
    microscope.beams.ion_beam.working_distance.value = (
        microscope_state.ib_settings.working_distance
    )
    microscope.beams.ion_beam.beam_current.value = (
        microscope_state.ib_settings.beam_current
    )
    microscope.beams.ion_beam.horizontal_field_width.value = (
        microscope_state.ib_settings.hfw
    )
    microscope.beams.ion_beam.scanning.resolution.value = (
        microscope_state.ib_settings.resolution
    )
    microscope.beams.ion_beam.scanning.dwell_time.value = (
        microscope_state.ib_settings.dwell_time
    )
    # microscope.beams.ion_beam.stigmator.value = microscope_state.ib_settings.stigmation

    logging.info(f"microscope state restored")
    return

