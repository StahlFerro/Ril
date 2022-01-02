import shutil

import PIL.Image
from PIL import Image
from pathlib import Path
from typing import List, Tuple
from pycore.core_funcs import stdio
from pycore.models.criterion import CriteriaBundle
from pycore.bin_funcs.imager_api import InternalImageAPI, GifsicleAPI
from pycore.imaging.generic import transform_image
from pycore.utility import filehandler, imageutils


def create_animated_gif(image_paths: List, out_full_path: Path, crbundle: CriteriaBundle) -> Path:
    """Generate an animated GIF image by first applying transformations and lossy compression on them (if specified)
        and then converting them into singular static GIF images to a temporary directory, before compiled by Gifsicle.

    Args:
        image_paths (List): List of path to each image in a sequence
        crbundle (CriteriaBundle): Bundle of animated image creation criteria to adhere to.
        out_full_path (Path): Complete output path with the target name of the GIF.

    Returns:
        Path: Path of the created GIF.
    """
    criteria = crbundle.create_aimg_criteria
    stdio.debug({"_build_gif crbundle": crbundle})
    black_bg = Image.new("RGBA", size=criteria.size)
    target_dir = filehandler.mk_cache_dir(prefix_name="tmp_gifrags")
    fcount = len(image_paths)
    if criteria.start_frame:
        image_paths = imageutils.shift_image_sequence(image_paths, criteria.start_frame)
    shout_nums = imageutils.shout_indices(fcount, 1)
    for index, ipath in enumerate(image_paths):
        if shout_nums.get(index):
            stdio.message(f"Processing frames... ({shout_nums.get(index)})")
        with Image.open(ipath) as im:
            im = transform_image(im, crbundle.create_aimg_criteria)
            im = gif_encode(im, crbundle, black_bg)

            fragment_name = str(ipath.name)
            if criteria.reverse:
                reverse_index = len(image_paths) - (index + 1)
                fragment_name = f"rev_{str.zfill(str(reverse_index), 6)}_{fragment_name}"
            else:
                fragment_name = f"{str.zfill(str(index), 6)}_{fragment_name}"
            save_path = target_dir.joinpath(f"{fragment_name}.gif")

            im.save(save_path)

    out_full_path = GifsicleAPI.combine_gif_images(target_dir, out_full_path, crbundle)
    shutil.rmtree(target_dir)
    # logger.control("CRT_FINISH")
    return out_full_path


def gif_encode(im: PIL.Image.Image, crbundle: CriteriaBundle, bg_im: PIL.Image.Image) -> PIL.Image.Image:
    """
    Encodes any Pillow image into a GIF image
    Args:
        im (Image): Pillow image
        crbundle: Criteria bundle
        bg_im: Fallback background image if the image will be saved without transparency

    Returns:
        Image: GIF-encoded image
    """
    criteria = crbundle.create_aimg_criteria
    gif_opt_criteria = crbundle.gif_opt_criteria
    transparency = im.info.get("transparency", False)
    if im.mode == "RGBA":
        if gif_opt_criteria.is_dither_alpha:
            stdio.debug(gif_opt_criteria.dither_alpha_threshold_value)
            stdio.debug(gif_opt_criteria.dither_alpha_method_enum)
            im = InternalImageAPI.dither_alpha(im, method=gif_opt_criteria.dither_alpha_method_enum,
                                               threshold=gif_opt_criteria.dither_alpha_threshold_value)
        if criteria.preserve_alpha:
            alpha = im.getchannel("A")
            im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
            mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
            im.paste(255, mask)
            im.info["transparency"] = 255
        else:
            bg_image = bg_im.copy()
            bg_image.alpha_composite(im)
            # im.show()
            im = bg_image
            # black_bg.show()
            im = im.convert("P", palette=Image.ADAPTIVE)
        # im.save(save_path)
    elif im.mode == "RGB":
        im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE)
        # im.save(save_path)
    elif im.mode == "P":
        if transparency:
            if type(transparency) is int:
                pass
                # im.save(save_path, transparency=transparency)
            else:
                im = im.convert("RGBA")
                alpha = im.getchannel("A")
                im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                im.paste(255, mask)
                im.info["transparency"] = 255
                # im.save(save_path)
        else:
            pass
            # im.save(save_path)
    return im
