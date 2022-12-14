import logging

import numpy as np
from autoscript_sdb_microscope_client import SdbMicroscopeClient
from autoscript_sdb_microscope_client.structures import (AdornedImage,
                                                         MoveSettings,
                                                         Rectangle,
                                                         StagePosition)
from scipy import fftpack

from fibsem import acquire, calibration, movement, utils, validation
from fibsem.imaging import masks
from fibsem.imaging import utils as image_utils
from fibsem.structures import (BeamType, ImageSettings, MicroscopeSettings,
                               ReferenceImages)


def correct_stage_eucentric_alignment(microscope: SdbMicroscopeClient, image_settings: ImageSettings, tilt_degrees: float = 25) -> None:

    # iteratively?
    # TODO: does the direction of tilt change this?

    # take images
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    
    # tilt stretch to match feature sizes 
    ib_image = image_utils.cosine_stretch(ib_image, tilt_degrees)

    # cross correlate
    lp_px = int(max(ib_image.data.shape) / 12)
    hp_px = int(max(ib_image.data.shape) / 256)
    sigma = 6

    dx, dy, xcorr = shift_from_crosscorrelation(
        eb_image, ib_image, lowpass=lp_px, highpass=hp_px, sigma=sigma, 
        use_rect_mask=True, ref_mask=None
    )

    # TODO: error check?
    shift_within_tolerance = validation.check_shift_within_tolerance(
        dx=dx, dy=dy, ref_image=eb_image, limit=0.5
    )

    # move vertically to correct eucentric position
    # TODO: check dy direction?
    movement.move_stage_eucentric_correction(microscope, dy)


def coarse_eucentric_alignment(microscope: SdbMicroscopeClient, hfw: float = 30e-6, eucentric_height: float = 3.91e-3) -> None:

    # focus and link stage
    calibration.auto_link_stage(microscope, hfw=hfw)

    # move to eucentric height
    stage = microscope.specimen.stage
    move_settings = MoveSettings(link_z_y=True)
    z_move = StagePosition(z=eucentric_height, coordinate_system="Specimen")
    stage.absolute_move(z_move, move_settings)


def beam_shift_alignment(
    microscope: SdbMicroscopeClient,
    image_settings: ImageSettings,
    ref_image: AdornedImage,
    reduced_area: Rectangle,
):
    """Align the images by adjusting the beam shift, instead of moving the stage
            (increased precision, lower range)
        NOTE: only shift the ion beam, never electron

    Args:
        microscope (SdbMicroscopeClient): autoscript microscope client
        image_settings (acquire.ImageSettings): settings for taking image
        ref_image (AdornedImage): reference image to align to
        reduced_area (Rectangle): The reduced area to image with.
    """

    # # align using cross correlation
    new_image = acquire.new_image(
        microscope, settings=image_settings, reduced_area=reduced_area
    )
    dx, dy, _ = shift_from_crosscorrelation(
        ref_image, new_image, lowpass=50, highpass=4, sigma=5, use_rect_mask=True
    )

    # adjust beamshift
    microscope.beams.ion_beam.beam_shift.value += (-dx, dy)


def correct_stage_drift(
    microscope: SdbMicroscopeClient,
    settings: MicroscopeSettings,
    reference_images: ReferenceImages,
    alignment: tuple(BeamType) = (BeamType.ELECTRON, BeamType.ELECTRON),
    rotate: bool = False,
    use_ref_mask: bool = False,
) -> bool:
    """Correct the stage drift by crosscorrelating low-res and high-res reference images"""

    # set reference images
    if alignment[0] is BeamType.ELECTRON:
        ref_lowres, ref_highres = (
            reference_images.low_res_eb,
            reference_images.high_res_eb,
        )
    if alignment[0] is BeamType.ION:
        ref_lowres, ref_highres = (
            reference_images.low_res_ib,
            reference_images.high_res_ib,
        )

    # rotate reference
    if rotate:
        ref_lowres = image_utils.rotate_image(ref_lowres)
        ref_highres = image_utils.rotate_image(ref_highres)

    # align lowres, then highres
    for ref_image in [ref_lowres, ref_highres]:

        if use_ref_mask:
            ref_mask = masks.create_lamella_mask(ref_image, settings.protocol["lamella"], scale = 4, use_trench_height=True) # TODO: refactor, liftout specific
        else: 
            ref_mask = None

        # take new images
        # set new image settings (same as reference)
        settings.image = utils.match_image_settings(
            ref_image, settings.image, beam_type=alignment[1]
        )
        new_image = acquire.new_image(microscope, settings.image)

        # crosscorrelation alignment
        ret = align_using_reference_images(
            microscope, settings, ref_image, new_image, ref_mask=ref_mask
        )

        if ret is False:
            break # cross correlation has failed...

    return ret

def align_using_reference_images(
    microscope: SdbMicroscopeClient,
    settings: MicroscopeSettings,
    ref_image: AdornedImage,
    new_image: AdornedImage,
    ref_mask: np.ndarray = None
) -> bool:

    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots(1, 2)
    # ax[0].imshow(ref_image.data, cmap="gray")
    # ax[1].imshow(new_image.data, cmap="gray")

    # plt.show()

    # get beam type
    ref_beam_type = BeamType[ref_image.metadata.acquisition.beam_type.upper()]
    new_beam_type = BeamType[new_image.metadata.acquisition.beam_type.upper()]

    logging.info(
        f"aligning {ref_beam_type.name} reference image to {new_beam_type.name}."
    )
    # lp_px = int(max(new_image.data.shape) * 0.66)
    # hp_px = int(max(new_image.data.shape) / 64)
    sigma = 6
    lp_px = int(max(new_image.data.shape) / 6)
    hp_px = int(max(new_image.data.shape) / 256)

    dx, dy, xcorr = shift_from_crosscorrelation(
        ref_image, new_image, lowpass=lp_px, highpass=hp_px, sigma=sigma, 
        use_rect_mask=True, ref_mask=ref_mask
    )

    shift_within_tolerance = validation.check_shift_within_tolerance(
        dx=dx, dy=dy, ref_image=ref_image, limit=0.5
    )

    if shift_within_tolerance:

        # move the stage
        movement.move_stage_relative_with_corrected_movement(microscope, 
            settings, 
            dx=dx, 
            # dy=dy,
            dy=-dy, 
            beam_type=new_beam_type)

    return shift_within_tolerance

def shift_from_crosscorrelation(
    ref_image: AdornedImage,
    new_image: AdornedImage,
    lowpass: int = 128,
    highpass: int = 6,
    sigma: int = 6,
    use_rect_mask: bool = False,
    ref_mask: np.ndarray = None
) -> tuple[float, float, np.ndarray]:

    # get pixel_size
    pixelsize_x = new_image.metadata.binary_result.pixel_size.x
    pixelsize_y = new_image.metadata.binary_result.pixel_size.y

    # normalise both images
    ref_data_norm = image_utils.normalise_image(ref_image)
    new_data_norm = image_utils.normalise_image(new_image)

    # cross-correlate normalised images
    if use_rect_mask:
        rect_mask = masks._mask_rectangular(new_data_norm.shape)
        ref_data_norm = rect_mask * ref_data_norm
        new_data_norm = rect_mask * new_data_norm

    if ref_mask is not None:
        ref_data_norm = ref_mask * ref_data_norm # mask the reference

    # import matplotlib.pyplot as plt
    # plt.imshow(ref_data_norm, cmap="gray")
    # plt.show()

    # run crosscorrelation
    xcorr = crosscorrelation(
        ref_data_norm, new_data_norm, bp=True, lp=lowpass, hp=highpass, sigma=sigma
    )

    # calculate maximum crosscorrelation
    maxX, maxY = np.unravel_index(np.argmax(xcorr), xcorr.shape)
    cen = np.asarray(xcorr.shape) / 2
    err = np.array(cen - [maxX, maxY], int)

    # calculate shift in metres
    x_shift = err[1] * pixelsize_x
    y_shift = err[0] * pixelsize_y # this could be the issue?
    
    logging.info(f"pixelsize: x: {pixelsize_x}, y: {pixelsize_y}")

    logging.info(f"cross-correlation:")
    logging.info(f"maxX: {maxX}, {maxY}, centre: {cen}")
    logging.info(f"x: {err[1]}px, y: {err[0]}px")
    logging.info(f"x: {x_shift:.2e}m, y: {y_shift:.2e} meters")

    # metres
    return x_shift, y_shift, xcorr


# TODO



def crosscorrelation(img1: np.ndarray, img2: np.ndarray,  
    lp: int = 128, hp: int = 6, sigma: int = 6, bp: bool = False) -> np.ndarray:
    """Cross-correlate images (fourier convolution matching)

    Args:
        img1 (np.ndarray): reference_image
        img2 (np.ndarray): new image
        lp (int, optional): lowpass. Defaults to 128.
        hp (int, optional): highpass . Defaults to 6.
        sigma (int, optional): sigma (gaussian blur). Defaults to 6.
        bp (bool, optional): use a bandpass. Defaults to False.

    Returns:
        np.ndarray: crosscorrelation map
    """
    if img1.shape != img2.shape:
        err = f"Image 1 {img1.shape} and Image 2 {img2.shape} need to have the same shape"
        logging.error(err)
        raise ValueError(err)

    if bp: 
        bandpass = masks.bandpass_mask(
            size=(img1.shape[1], img1.shape[0]), 
            lp=lp, hp=hp, sigma=sigma
        )
        n_pixels = img1.shape[0] * img1.shape[1]
        
        img1ft = fftpack.ifftshift(bandpass * fftpack.fftshift(fftpack.fft2(img1)))
        tmp = img1ft * np.conj(img1ft)
        img1ft = n_pixels * img1ft / np.sqrt(tmp.sum())
        
        img2ft = fftpack.ifftshift(bandpass * fftpack.fftshift(fftpack.fft2(img2)))
        img2ft[0, 0] = 0
        tmp = img2ft * np.conj(img2ft)
        
        img2ft = n_pixels * img2ft / np.sqrt(tmp.sum())

        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots(1, 2, figsize=(15, 15))
        # ax[0].imshow(fftpack.ifft2(img1ft).real)
        # ax[1].imshow(fftpack.ifft2(img2ft).real)
        # plt.show()

        xcorr = np.real(fftpack.fftshift(fftpack.ifft2(img1ft * np.conj(img2ft))))
    else: # TODO: why are these different...
        img1ft = fftpack.fft2(img1)
        img2ft = np.conj(fftpack.fft2(img2))
        img1ft[0, 0] = 0
        xcorr = np.abs(fftpack.fftshift(fftpack.ifft2(img1ft * img2ft)))
    
    return xcorr

# numpy version
def crosscorrelation_v2_np(img1: np.ndarray, img2: np.ndarray,  
    lp: int = 128, hp: int = 6, sigma: int = 6, bp: bool = False) -> np.ndarray:
    """Cross-correlate images (fourier convolution matching)

    Args:
        img1 (np.ndarray): reference_image
        img2 (np.ndarray): new image
        lp (int, optional): lowpass. Defaults to 128.
        hp (int, optional): highpass . Defaults to 6.
        sigma (int, optional): sigma (gaussian blur). Defaults to 6.
        bp (bool, optional): use a bandpass. Defaults to False.

    Returns:
        np.ndarray: crosscorrelation map
    """
    if img1.shape != img2.shape:
        err = f"Image 1 {img1.shape} and Image 2 {img2.shape} need to have the same shape"
        logging.error(err)
        raise ValueError(err)

    if bp: 
        bandpass = masks.bandpass_mask(
            size=(img1.shape[1], img1.shape[0]), 
            lp=lp, hp=hp, sigma=sigma
        )
        n_pixels = img1.shape[0] * img1.shape[1]
        
        img1ft = np.fft.ifftshift(bandpass * np.fft.fftshift(np.fft.fft2(img1)))
        tmp = img1ft * np.conj(img1ft)
        img1ft = n_pixels * img1ft / np.sqrt(tmp.sum())
        
        img2ft = np.fft.ifftshift(bandpass * np.fft.fftshift(np.fft.fft2(img2)))
        img2ft[0, 0] = 0
        tmp = img2ft * np.conj(img2ft)
        
        img2ft = n_pixels * img2ft / np.sqrt(tmp.sum())

        xcorr = np.real(np.fft.fftshift(np.fft.ifft2(img1ft * np.conj(img2ft))))
    else: # TODO: why are these different...
        img1ft = np.fft.fft2(img1)
        img2ft = np.conj(np.fft.fft2(img2))
        img1ft[0, 0] = 0
        xcorr = np.abs(np.fft.fftshift(np.fft.ifft2(img1ft * img2ft)))
    
    return xcorr
