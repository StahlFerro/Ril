import os
import io
import string
import shutil
import math
import time
import subprocess
import tempfile
from random import choices
from pprint import pprint
from urllib.parse import urlparse
from typing import List, Dict, Tuple
from datetime import datetime

from PIL import Image
from apng import APNG, PNG
from hurry.filesize import size, alternative

from .core_funcs.config import IMG_EXTS, ANIMATED_IMG_EXTS, STATIC_IMG_EXTS, ABS_CACHE_PATH, ABS_TEMP_PATH, imager_exec_path
from .core_funcs.criterion import CreationCriteria, SplitCriteria, ModificationCriteria
from .core_funcs.utility import _mk_temp_dir, _reduce_color, _unoptimize_gif, _log, _restore_disposed_frames, shout_indices
from .core_funcs.arg_builder import gifsicle_args, imagemagick_args, apngopt_args, pngquant_args
from .create_ops import create_aimg
from .split_ops import split_aimg, _fragment_apng_frames


def _gifsicle_modify(sicle_args: List[Tuple[str, str]], target_path: str, out_full_path: str, total_ops: int) -> str:
    yield {"sicle_args": sicle_args}
    gifsicle_path = imager_exec_path('gifsicle')
    for index, (arg, description) in enumerate(sicle_args, start=1):
        yield {"msg": f"index {index}, arg {arg}, description: {description}"}
        cmdlist = [gifsicle_path, arg, f'"{target_path}"', "--output", f'"{out_full_path}"']
        cmd = ' '.join(cmdlist)
        yield {"msg": f"[{index}/{total_ops}] {description}"}
        yield {"cmd": cmd}
        subprocess.run(cmd, shell=True)
        if target_path != out_full_path:
            target_path = out_full_path
    return target_path


def _imagemagick_modify(magick_args: List[Tuple[str, str]], target_path: str, out_full_path: str, total_ops: int, shift_index: int) -> str:
    yield {"magick_args": magick_args}
    imagemagick_path = imager_exec_path('imagemagick')
    for index, (arg, description) in enumerate(magick_args, start=1):
        yield {"msg": f"index {index}, arg {arg}, description: {description}"}
        cmdlist = [imagemagick_path, arg, f'"{target_path}"', "--output", f'"{out_full_path}"']
        cmd = ' '.join(cmdlist)
        yield {"msg": f"[{shift_index + index}/{total_ops}] {description}"}
        yield {"cmd": cmd}
        subprocess.run(cmd, shell=True)
        if target_path != out_full_path:
            target_path = out_full_path
    return target_path


def _apngopt_modify(aopt_args: List[Tuple[str, str]], target_path: str, out_full_path: str, total_ops: int, shift_index: int):
    yield {"aopt_args": aopt_args}
    apngopt_path = imager_exec_path('apngopt')
    # cwd = subprocess.check_output('pwd', shell=True).decode('utf-8')
    cwd = str(os.getcwd())
    common_path = os.path.commonpath([target_path, out_full_path, apngopt_path])
    target_rel_path = os.path.relpath(target_path, cwd)
    out_rel_path = os.path.relpath(out_full_path, cwd)
    # raise Exception(apngopt_path, common_path, target_rel_path, out_rel_path)
    # result = subprocess.check_output('pwd', shell=True).decode('utf-8')
    yield {"cwd": cwd}
    # yield {"pcwd": os.getcwd()}
    for index, (arg, description) in enumerate(aopt_args, start=1):
        yield {"msg": f"index {index}, arg {arg}, description: {description}"}
        cmdlist = [apngopt_path, arg, f'"{target_rel_path}"', f'"{out_rel_path}"']
        cmd = ' '.join(cmdlist)
        yield {"msg": f"[{shift_index + index}/{total_ops}] {description}"}
        yield {"cmd": cmd}
        result = subprocess.check_output(cmd, shell=True)
        # yield {"out": result}
        if target_path != out_full_path:
            target_path = out_full_path
    return target_path
    # yield {"aopt_args": aopt_args}
    # opt_dir = _mk_temp_dir(prefix_name='apngopt_dir')
    # apng_name = os.path.basename(target_path)
    # apngopt_path = shutil.copyfile(imager_exec_path('apngopt'), os.path.join(opt_dir, 'apngopt'))
    # apng_copied = os.path.basename(shutil.copyfile(target_path, os.path.join(opt_dir, apng_name)))
    # for index, (arg, description) in enumerate(aopt_args, start=1):
    #     yield {"msg": f"index {index}, arg {arg}, description: {description}"}
    #     cmdlist = [apngopt_path, arg, f'"{apng_copied}"', f'"{apng_copied}"']
    #     # raise Exception(cmdlist, out_full_path)
    #     cmd = ' '.join(cmdlist)
    #     yield {"msg": f"[{shift_index + index}/{total_ops}] {description}"}
    #     yield {"cmd": cmd}
    #     result = subprocess.check_output(cmd, shell=True)
    #     yield {"out": result}
    #     if target_path != out_full_path:
    #         target_path = out_full_path
    # return target_path


# def _internal_gif_reverse(target_path: str, out_full_path: str, mod_criteria: ModificationCriteria, total_ops: int, shift_index: int = 0):
#     frames_dir = _mk_temp_dir(prefix_name="formod_frames")
#     split_criteria = SplitCriteria({
#         'pad_count': 6,
#         'color_space': "",
#         'is_duration_sensitive': True,
#         'is_unoptimized': mod_criteria.is_unoptimized,
#     })
#     # yield {"msg": split_criteria.__dict__}
#     yield from split_aimg(target_path, frames_dir, split_criteria)


def _internal_apng_modify(target_path: str, out_full_path: str, mod_criteria: ModificationCriteria, total_ops: int, shift_index: int = 0):
    """ Splits the APNG apart into frames, apply modification to each frames, and then compile them back """
    apng = APNG.open(target_path)
    new_apng = APNG()
    yield {"log": "Internal APNG Modification"}
    split_criteria = SplitCriteria({
        'pad_count': 6,
        'color_space': "",
        'is_duration_sensitive': True,
        'is_unoptimized': True,
    })
    frames = yield from _fragment_apng_frames(apng, split_criteria)
    if mod_criteria.is_reversed:
        frames.reverse()
    if mod_criteria.apng_is_lossy:
        frames = yield from _batch_quantize(frames, mod_criteria)
    for im in frames:
        # im.show()
        # with io.BytesIO() as bytebox:
        #     png.save(bytebox)
        #     with Image.open(bytebox) as im:
        if mod_criteria.flip_x:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        if mod_criteria.flip_y:
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
        if mod_criteria.is_reversed or mod_criteria.must_resize():
            im = im.resize((mod_criteria.width, mod_criteria.height))
        newbox = io.BytesIO()
        im.save(newbox, format="PNG")
        new_apng.append(PNG.from_bytes(newbox.getvalue()), delay=int(mod_criteria.delay * 1000))
    new_apng.save(out_full_path)
    return out_full_path

def _batch_quantize(frames: List[Image.Image], criteria: ModificationCriteria):
    """ Perform PNG quantization on a list of PIL.Image.Images using PNGQuant """
    quantized_frames = []
    pngquant_exec = imager_exec_path("pngquant")
    q_ops = pngquant_args(criteria)
    quant_dir = _mk_temp_dir(prefix_name="quant_dir")
    shout_nums = shout_indices(len(frames), 5)
    for index, fr in enumerate(frames):
        if shout_nums.get(index):
            yield {"msg": f'Quantizing PNG... ({shout_nums.get(index)})'}
        save_path = os.path.join(quant_dir, f"{index}.png")
        out_path = os.path.join(quant_dir, f"{index}_quantized.png")
        yield {"FMODE": fr.mode}
        fr.save(save_path, "PNG")
        args = [pngquant_exec, ' '.join([q[0] for q in q_ops]), save_path, "--output", out_path]
        cmd = ' '.join(args)
        yield {"cmd": cmd}
        result = subprocess.check_output(cmd, shell=True)
        # yield {"out": result}
        quantized_img = Image.open(out_path)
        yield {"QMODE": quantized_img.mode}
        quantized_img = quantized_img.convert("RGBA")
        quantized_frames.append(quantized_img)
    # yield {"ssdsdsssdsd": quantized_frames}
    return quantized_frames

def _rebuild_aimg(img_path: str, out_dir: str, mod_criteria: ModificationCriteria):
    yield {"DEBUG": [img_path, out_dir]}
    """ Splits a GIF/APNG into frames, and then recompile them back into an AIMG. Used to change their format, or reverse the animation"""
    frames_dir = _mk_temp_dir(prefix_name="formod_frames")
    split_criteria = SplitCriteria({
        'pad_count': 6,
        'color_space': "",
        'is_duration_sensitive': True,
        'is_unoptimized': mod_criteria.is_unoptimized,
    })
    # yield {"msg": split_criteria.__dict__}
    yield from split_aimg(img_path, frames_dir, split_criteria)
    frames = [str(os.path.join(frames_dir, f)) for f in sorted(os.listdir(frames_dir))]
    yield {"frames_dir": frames_dir}
    yield {"frames": frames}
    ds_fps = mod_criteria.orig_frame_count_ds / mod_criteria.orig_loop_duration
    ds_delay = 1 / ds_fps
    create_criteria = CreationCriteria({
        'fps': ds_fps,
        'delay': ds_delay,
        'format': mod_criteria.format,
        'is_reversed': mod_criteria.is_reversed,
        'is_transparent': True,
        'flip_x': False, # Flipping horizontally is handled by gifsicle
        'flip_y': False, # Flipping vertically is handled by gifsicle
        'width': mod_criteria.width,
        'height': mod_criteria.height,
        'loop_count': mod_criteria.loop_count
    })
    new_image_path = yield from create_aimg(frames, out_dir, os.path.basename(img_path), create_criteria)
    return new_image_path


def modify_aimg(img_path: str, out_dir: str, criteria: ModificationCriteria):
    img_path = os.path.abspath(img_path)
    # raise Exception(img_path, out_dir, criteria)
    if not os.path.isfile(img_path):
        raise Exception("Cannot Preview/Modify the image. The original file in the system may been removed.")
    out_dir = os.path.abspath(out_dir)
    full_name = f"{criteria.name}.{criteria.format.lower()}"
    orig_full_name = f"{criteria.name}.{criteria.orig_format.lower()}"
    # temp_dir = _mk_temp_dir(prefix_name="temp_mods")
    # temp_save_path = os.path.join(temp_dir, full_name)
    out_full_path = os.path.join(out_dir, full_name)
    orig_out_full_path = os.path.join(out_dir, orig_full_name)
    yield {"msg": f"OUT FULL PATH: {out_full_path}"}
    sicle_args = gifsicle_args(criteria)
    magick_args = imagemagick_args(criteria)
    aopt_args = apngopt_args(criteria)
    # yield sicle_args
    target_path = str(img_path)
    total_ops = len(sicle_args) + len(magick_args) + len(aopt_args)
    
    if criteria.change_format():
        if criteria.orig_format == "GIF":
            if sicle_args:
                target_path = yield from _gifsicle_modify(sicle_args, target_path, orig_out_full_path, total_ops)
            if magick_args:
                target_path = yield from _imagemagick_modify(magick_args, target_path, orig_out_full_path, total_ops, len(sicle_args))
            # yield {"preview_path": target_path}
            yield {"msg": f"Changing format ({criteria.orig_format} -> {criteria.format})"}
            target_path = yield from _rebuild_aimg(target_path, out_dir, criteria)
        elif criteria.orig_format == "PNG":
            yield {"msg": f"Changing format ({criteria.orig_format} -> {criteria.format})"}
            target_path = yield from _rebuild_aimg(target_path, out_dir, criteria)
            out_full_path = str(target_path)
            if sicle_args:
                target_path = yield from _gifsicle_modify(sicle_args, target_path, out_full_path, total_ops)
            if magick_args:
                target_path = yield from _imagemagick_modify(magick_args, target_path, out_full_path, total_ops, len(sicle_args))             
            # yield {"preview_path": target_path}
    else:
        if criteria.orig_format == "GIF":
            if criteria.is_reversed:
                target_path = yield from _rebuild_aimg(target_path, out_dir, criteria)
            if sicle_args:
                target_path = yield from _gifsicle_modify(sicle_args, target_path, orig_out_full_path, total_ops)
            if magick_args:
                target_path = yield from _imagemagick_modify(magick_args, target_path, orig_out_full_path, total_ops, len(sicle_args))
            # yield {"preview_path": target_path}
        elif criteria.orig_format == "PNG":
            if criteria.has_general_alterations():
                target_path = yield from _internal_apng_modify(target_path, out_full_path, criteria, total_ops)
            if aopt_args:
                target_path = yield from _apngopt_modify(aopt_args, target_path, out_full_path, total_ops, len(sicle_args) + len(magick_args))
    yield {"preview_path": target_path}

    yield {"CONTROL": "MOD_FINISH"}
