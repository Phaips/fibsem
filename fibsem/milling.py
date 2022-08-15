
from fibsem import constants
import logging
import numpy as np
from autoscript_sdb_microscope_client import SdbMicroscopeClient
from fibsem.structures import BeamType, MillingSettings

from autoscript_sdb_microscope_client._dynamic_object_proxies import CleaningCrossSectionPattern, RectanglePattern
from typing import Union

########################### SETUP 

# TODO: remove, unused?
def reset_state(microscope: SdbMicroscopeClient, settings: dict, application_file=None):
    """Reset the microscope state.
    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.
    application_file : str, optional
        Name of the application file for milling, by default None
    """
    microscope.patterning.clear_patterns()
    if application_file:  # optionally specified
        microscope.patterning.set_default_application_file(application_file)
    microscope.beams.ion_beam.scanning.resolution.value = settings["imaging"]["resolution"]
    microscope.beams.ion_beam.scanning.dwell_time.value = settings["imaging"]["dwell_time"]
    microscope.beams.ion_beam.horizontal_field_width.value =  settings["imaging"]["horizontal_field_width"]
    microscope.imaging.set_active_view(2)  # the ion beam view
    microscope.patterning.set_default_beam_type(2)  # ion beam default
    return microscope


def setup_milling(
    microscope: SdbMicroscopeClient,
    application_file: str = "autolamella",
    patterning_mode: str = "Serial",
    hfw:float = 100e-6,
):
    """Setup Microscope for Ion Beam Milling.

    Args:
        microscope (SdbMicroscopeClient): AutoScript microscope instance
        application_file (str, optional): Application file for ion beam milling. Defaults to "autolamella".
        patterning_mode (str, optional): Ion beam milling patterning mode. Defaults to "Serial".
        hfw (float, optional): horizontal field width for milling. Defaults to 100e-6.
    """

    # microscope.imaging.set_active_device(BeamType.ION.value) # TODO: change over
    microscope.imaging.set_active_view(BeamType.ION.value)  # the ion beam view
    microscope.patterning.set_default_beam_type(BeamType.ION.value)  # ion beam default
    microscope.patterning.set_default_application_file(application_file)
    microscope.patterning.mode = patterning_mode
    microscope.patterning.clear_patterns()  # clear any existing patterns
    microscope.beams.ion_beam.horizontal_field_width.value = hfw
    logging.info(f"setup ion beam milling")
    logging.info(f"application file:  {application_file}, pattern mode: {patterning_mode}, hfw: {hfw}")


def run_milling(
    microscope: SdbMicroscopeClient,
    settings: dict,
    milling_current: float,
    asynch: bool = False,
) -> None:
    """Run Ion Beam Milling.

    Args:
        microscope (SdbMicroscopeClient): AutoScript microscope instance
        settings (dict): settings dictionary
        milling_current (float, optional): ion beam milling current. Defaults to None.
        asynch (bool, optional): flag to run milling asynchronously. Defaults to False.
    """   
    # change to milling current
    microscope.imaging.set_active_view(2)  # the ion beam view
    if microscope.beams.ion_beam.beam_current.value != milling_current:
        # if milling_current not in microscope.beams.ion_beam.beam_current.available_values:
        #   switch to closest
        logging.info(f"changing to milling current: {milling_current:.2e}")
        microscope.beams.ion_beam.beam_current.value = milling_current

    # run milling (asynchronously)
    logging.info(f"running ion beam milling now... asynchronous={asynch}")
    if asynch:
        microscope.patterning.start()
    else:
        microscope.patterning.run()
        microscope.patterning.clear_patterns()


def finish_milling(microscope: SdbMicroscopeClient, imaging_current: float = 20e-12) -> None:
    """Clear milling patterns, and restore to the imaging current.   
    
    Args:
        microscope (SdbMicroscopeClient): AutoScript microscope instance
        imaging_current (float, optional): Imaging Current. Defaults to 20e-12.
    
    """
    # restore imaging current
    logging.info(f"changing to imaging current: {imaging_current:.2e}")
    microscope.patterning.clear_patterns()
    microscope.beams.ion_beam.beam_current.value = imaging_current
    microscope.patterning.mode = "Serial"
    logging.info("finished ion beam milling.")


############################# UTILS #############################

def read_protocol_dictionary(settings: dict, stage_name: str) -> list[dict]:
    """Read the milling protocol settings dictionary into a structured format

    Args:
        settings (dict): settings dictionary
        stage_name (str): milling stage name

    Returns:
        list[dict]: milling protocol stages
    """
    # multi-stage
    if "protocol_stages" in settings[stage_name]:
        protocol_stages = []
        for stage_settings in settings[stage_name]["protocol_stages"]:
            tmp_settings = settings[stage_name].copy()
            tmp_settings.update(stage_settings)
            protocol_stages.append(tmp_settings)
    # single-stage
    else:
        protocol_stages = [settings[stage_name]]

    return protocol_stages


def calculate_milling_time(patterns: list, milling_current: float) -> float:

    from fibsem import config 

    # volume (width * height * depth) / total_volume_sputter_rate

    # calculate sputter rate
    if milling_current in config.MILLING_SPUTTER_RATE:
        total_volume_sputter_rate = config.MILLING_SPUTTER_RATE[milling_current]
    else:
        total_volume_sputter_rate = 3.920e-1

    # calculate total milling volume
    volume = 0
    for stage in patterns:
        for pattern in stage:
            width = pattern.width * constants.METRE_TO_MICRON
            height = pattern.height * constants.METRE_TO_MICRON
            depth = pattern.depth * constants.METRE_TO_MICRON
            volume += width * height * depth
    
    # estimate time
    milling_time_seconds = volume / total_volume_sputter_rate # um3 * 1/ (um3 / s) = seconds

    logging.info(f"WHDV: {width:.2f}um, {height:.2f}um, {depth:.2f}um, {volume:.2f}um3")
    logging.info(f"Volume: {volume:.2e}, Rate: {total_volume_sputter_rate:.2e} um3/s")
    logging.info(f"Milling Estimated Time: {milling_time_seconds / 60:.2f}m")

    return milling_time_seconds

### PATTERNING

def _draw_rectangle_pattern(microscope:SdbMicroscopeClient, settings:dict , x: float = 0.0, y: float = 0.0):

    if settings["cleaning_cross_section"]:
        pattern = microscope.patterning.create_cleaning_cross_section(
        center_x=x,
        center_y=y,
        width=settings["width"],
        height=settings["height"],
        depth=settings["depth"],
    )
    else:
        pattern = microscope.patterning.create_rectangle(
            center_x=x,
            center_y=y,
            width=settings["width"],
            height=settings["height"],
            depth=settings["depth"],
        )
    
    # need to make each protocol setting have these....which means validation
    pattern.rotation=np.deg2rad(settings["rotation"])
    pattern.scan_direction = settings["scan_direction"]

    return pattern


def _draw_rectangle_pattern_v2(microscope:SdbMicroscopeClient, mill_settings: MillingSettings) -> Union[CleaningCrossSectionPattern, RectanglePattern]:
    """Draw a rectangular milling pattern from settings

    Args:
        microscope (SdbMicroscopeClient): AutoScript microscope instance
        mill_settings (MillingSettings): milling pattern settings

    Returns:
        Union[CleaningCrossSectionPattern, RectanglePattern]: milling pattern
    """
    if mill_settings.cleaning_cross_section:
        pattern = microscope.patterning.create_cleaning_cross_section(
        center_x=mill_settings.centre_x,
        center_y=mill_settings.centre_x,
        width=mill_settings.width,
        height=mill_settings.height,
        depth=mill_settings.depth,
    )
    else:
        pattern = microscope.patterning.create_rectangle(
            center_x=mill_settings.centre_x,
            center_y=mill_settings.centre_y,
            width=mill_settings.width,
            height=mill_settings.height,
            depth=mill_settings.depth,
        )


    pattern.rotation=mill_settings.rotation
    pattern.scan_direction = mill_settings.scan_direction

    return pattern


def estimate_milling_time_in_seconds(milling_stage_patterns: list[list[Union[CleaningCrossSectionPattern, RectanglePattern]]]) -> float:
    """Calculate the estimated milling time for all milling patterns in a milling stage.

    Args:
        milling_stage_patterns (list[list[Union[CleaningCrossSectionPattern, RectanglePattern]]]): milling patterns for each stage

    Returns:
        float: estimated milling time (seconds)
    """
    total_time_seconds = 0
    for patterns in milling_stage_patterns:
        for pattern in patterns:
            total_time_seconds += pattern.time
    
    return total_time_seconds