import os
import io
import string
import shutil
import math
from random import choices
from pprint import pprint
from urllib.parse import urlparse
from typing import List

from PIL import Image
from apng import APNG, PNG

from .core_funcs.config import IMG_EXTS, ANIMATED_IMG_EXTS, STATIC_IMG_EXTS
from .core_funcs.criterion import SpritesheetBuildCriteria, SpritesheetSliceCriteria
from .utility import filehandler, imageutils


def _get_boxes(
    tile_width,
    tile_height,
    hbox_count,
    vbox_count,
    offset_x=0,
    offset_y=0,
    padding_x=0,
    padding_y=0,
):
    # hbox_count = math.ceil(sheet_width / tile_width)
    # vbox_count = math.ceil(sheet_height / tile_height)
    for v in range(0, vbox_count):
        for h in range(0, hbox_count):
            top = tile_height * v + offset_y + (padding_y * v)
            left = tile_width * h + offset_x + (padding_x * h)
            # bottom = min(top + tile_height, sheet_height)
            # right = min(left + tile_width, sheet_width)
            bottom = top + tile_height
            right = left + tile_width
            box = (left, top, right, bottom)
            yield box


def _slice_spritesheet(image_path: str, out_dir: str, filename: str, criteria: SpritesheetSliceCriteria):
    sheet = Image.open(os.path.abspath(image_path))
    hbox_count = criteria.sheet_width / criteria.tile_width
    vbox_count = criteria.sheet_height / criteria.tile_height
    boxes = _get_boxes(criteria.tile_width, criteria.tile_height, hbox_count, vbox_count)
    alpha_layer = Image.new("RGBA", (criteria.tile_width, criteria.tile_height))
    for index, box in enumerate(boxes):
        cut_frame = sheet.crop(box).convert("RGBA")
        # cut_frame = cut_frame.convert("RGBA")
        if criteria.is_edge_alpha and cut_frame.size != (
            criteria.tile_width,
            criteria.tile_height,
        ):
            alpha_copy = alpha_layer.copy()
            alpha_copy.alpha_composite(cut_frame)
            cut_frame = alpha_copy
        yield {"msg": cut_frame.size}
        save_name = os.path.join(out_dir, f"{filename}_{str(index).zfill(3)}.png")
        cut_frame.save(save_name)
    # yield {"msg": boxes}
    # yield {"msg": "e"}
    yield {"CONTROL": "SSPR_FINISH"}


def _build_spritesheet(image_paths: List, out_dir: str, filename: str, criteria: SpritesheetBuildCriteria):
    abs_image_paths = [os.path.abspath(ip) for ip in image_paths if os.path.exists(ip)]
    img_paths = [
        f for f in abs_image_paths if str.lower(os.path.splitext(f)[1][1:]) in set(STATIC_IMG_EXTS + ANIMATED_IMG_EXTS)
    ]
    # workpath = os.path.dirname(img_paths[0])
    # Test if inputted filename has extension, then remove it from the filename
    # fname, ext = os.path.splitext(filename)
    # if ext:
    #     filename = fname
    if not out_dir:
        raise Exception("No output folder selected, please select it first")
    out_dir = os.path.abspath(out_dir)
    if not os.path.exists(out_dir):
        raise Exception("The specified absolute out_dir does not exist!")
    input_mode = criteria.input_format
    frames = []
    if input_mode == "sequence":
        frames = [Image.open(i) for i in img_paths]
    elif input_mode == "aimg":
        aimg = img_paths[0]
        ext = os.path.splitext(aimg)[1][1:]
        if ext.lower() == "gif":
            gif: Image = Image.open(aimg)
            for cr in range(0, gif.n_frames):
                gif.seek(cr)
                bytebox = io.BytesIO()
                gif.save(bytebox, "PNG", optimize=True)
                frames.append(Image.open(bytebox))
                yield {"msg": f"Splitting GIF... ({cr + 1}/{gif.n_frames})"}
        elif ext.lower() == "png":
            raise Exception("APNG!")
        else:
            raise Exception("Unknown image format!")
    else:
        raise Exception("Unknown input image mode!")
    # tile_width = frames[0].size[0]
    # tile_height = frames[0].size[1]
    tile_width = criteria.tile_width
    tile_height = criteria.tile_height
    fcount = len(frames)
    max_frames_row = criteria.tiles_per_row
    if fcount > max_frames_row:
        spritesheet_width = tile_width * max_frames_row
        required_rows = math.ceil(fcount / max_frames_row)
        # print('required rows', required_rows)
        spritesheet_height = tile_height * required_rows
    else:
        spritesheet_width = tile_width * fcount
        spritesheet_height = tile_height

    hbox_count = int(spritesheet_width / tile_width)
    vbox_count = int(spritesheet_height / tile_height)

    spritesheet_width += criteria.offset_x
    spritesheet_height += criteria.offset_y

    spritesheet_width += hbox_count * criteria.padding_x * 2 - ((hbox_count + 1) * criteria.padding_x)
    spritesheet_height += vbox_count * criteria.padding_y * 2 - ((vbox_count + 1) * criteria.padding_y)

    spritesheet = Image.new("RGBA", (int(spritesheet_width), int(spritesheet_height)))
    # spritesheet.save(os.path.join(out_dir,"Ok.png"), "PNG")
    # boxes = []
    yield {"msg": "Placing frames to sheet..."}
    perc_skip = 5
    shout_nums = shout_indices(fcount, perc_skip)
    yield {"msg": shout_nums}
    # yield {"msg": shout_indices}
    # raise Exception(shout_indices)
    boxes = list(
        _get_boxes(
            tile_width,
            tile_height,
            hbox_count,
            vbox_count,
            criteria.offset_x,
            criteria.offset_y,
            criteria.padding_x,
            criteria.padding_y,
        )
    )
    yield {"msg": boxes}
    for index, fr in enumerate(frames):

        orig_width, orig_height = fr.size
        must_resize = criteria.tile_width != orig_width or criteria.tile_height != orig_height
        if must_resize:
            fr = fr.resize((round(criteria.tile_width), round(criteria.tile_height)))
            # yield {"msg": f"RESIZING {must_resize}"}
        # top = tile_height * math.floor(index / max_frames_row) + criteria.offset_y
        # left = tile_width * (index % max_frames_row) + criteria.offset_x
        # bottom = top + tile_height
        # right = left + tile_width

        # box = (left, top, right, bottom)
        # box = [int(b) for b in box]

        cut_frame = fr.crop((0, 0, tile_width, tile_height))
        spritesheet.paste(cut_frame, boxes[index])
        cut_frame.close()
        if shout_nums.get(index):
            yield {"msg": f"Placing frames to sheet... ({shout_nums.get(index)})"}
        # boxes.append(box)
    outfilename = f"{filename}.png"
    final_path = os.path.join(out_dir, outfilename)
    yield {"msg": f"Saving the file..."}
    spritesheet.MAX_IMAGE_PIXELS = None
    spritesheet.save(final_path, "PNG")
    yield {"msg": "closing up images..."}
    if input_mode == "sequence":
        for f in frames:
            f.close()
    spritesheet.close()
    yield {"preview_path": final_path}
    yield {"CONTROL": "BSPR_FINISH"}
    # raise Exception('yo')
