#!/usr/bin/env python2

import os
import re
import gimpfu
from gimpfu import gimp, pdb

# t = gimpfu.gettext.translation('gimp-scan-cutter', gimp.locale_directory, fallback=True)
# _ = t.ugettext

def cutter_single_image(
        image, drawable,
        limit, sl_thresh, sz_thresh,
        bg_manual, bg_color, bg_corner, bg_x, bg_y,
        padding, deskew, sq_crop, autoclose,
        save_same, save_dir, save_ftype, save_dpi, jpg_qual, save_suffix
    ):
    img_width = pdb.gimp_image_width(image)
    img_height = pdb.gimp_image_height(image)
    img_fullpath = pdb.gimp_image_get_filename(image)
    img_filename = os.path.basename(img_fullpath)
    img_name = '.'.join(img_filename.split('.')[:-1])
    img_ext = save_ftype or img_filename.split('.')[-1].lower()
    new_filename_tpl = ''.join([
        img_name, '-', save_suffix, '-',
        '%0', str(len(str(int(limit + 1)))), 'd',
        '.', img_ext
    ])
    new_fullpath_tpl = os.path.join(
        os.path.dirname(img_fullpath) if save_same else save_dir,
        new_filename_tpl
    )

    # gimp.message(new_fullpath_tpl)

    # function code goes here...
    gimp.context_push()
    pdb.gimp_image_undo_disable(image)

    # If the background wasn't manually defined, pick the colour from one of the four corners
    # (using radius 5 average)
    if not bg_manual:
        if bg_corner in (1, 3):
            bg_x = img_width - bg_x
        if bg_corner in (2, 3):
            bg_y = img_height - bg_y

        bg_color = pdb.gimp_image_pick_color(image, drawable, bg_x, bg_y, True, True, 5)

    pdb.gimp_context_set_defaults()
    pdb.gimp_context_set_antialias(True)
    pdb.gimp_context_set_sample_transparent(True)
    pdb.gimp_context_set_sample_threshold_int(sl_thresh)
    pdb.gimp_context_set_feather(True)
    fr = min(img_width, img_height) / 100.0     # NOTE why???
    pdb.gimp_context_set_feather_radius(fr, fr)
    pdb.gimp_context_set_background(bg_color)

    pdb.gimp_image_select_color(image, gimpfu.CHANNEL_OP_REPLACE, drawable, bg_color)

    # convert inverted copy of the background selection to a path
    pdb.gimp_selection_sharpen(image)
    pdb.gimp_selection_invert(image)

    # _, before = pdb.gimp_image_get_vectors(image)
    pdb.plug_in_sel2path(image, drawable)
    # _, after = pdb.gimp_image_get_vectors(image)
    # newpath_id = list(set(after) - set(before))[0]
    # newpath = gimp.Vectors.from_id(newpath_id)

    # looks like newly created vector is always active, so this should be sufficent
    newpath = pdb.gimp_image_get_active_vectors(image)

    pdb.gimp_context_set_feather(False)

    _, strokes = pdb.gimp_vectors_get_strokes(newpath)
    extracted = 0
    for stroke_id in strokes:
        stroke_points = pdb.gimp_vectors_stroke_get_points(newpath, stroke_id)
        # skip not closed paths
        if not stroke_points[3]:
            continue

        temp_vector = pdb.gimp_vectors_new(image, '-temp-')
        pdb.gimp_image_insert_vectors(image, temp_vector, None, -1)

        pdb.gimp_vectors_stroke_new_from_points(temp_vector, *stroke_points)
        pdb.gimp_image_select_item(image, gimpfu.CHANNEL_OP_REPLACE, temp_vector)
        pdb.gimp_image_remove_vectors(image, temp_vector)

        # check for minimum size
        bounds = pdb.gimp_selection_bounds(image)
        sizex = bounds[3] - bounds[1]
        sizey = bounds[4] - bounds[2]

        if (min(sizex, sizey) < sz_thresh or
                sizex >= img_width or
                sizey >= img_height):
            continue

        buffname = "dsibuff"
        if deskew and pdb.gimp_procedural_db_proc_exists('gimp_deskew_plugin'):
            pdb.gimp_progress_set_text('Running deskew plugin...')
            pdb.gimp_image_select_rectangle(
                image, gimpfu.CHANNEL_OP_REPLACE,
                bounds[1], bounds[2], sizex, sizey
            )
            buffname = pdb.gimp_edit_named_copy(drawable, buffname)
            temp_image = pdb.gimp_edit_named_paste_as_new(buffname)
            temp_layer = pdb.gimp_image_get_active_layer(temp_image)
            pdb.gimp_image_undo_disable(temp_image)

            pdb.gimp_layer_flatten(temp_layer)

            # RUN_NONINTERACTIVE causes 'calling error' exception
            pdb.gimp_deskew_plugin(temp_image, temp_layer, 0, 0, 0, 0, True,
                                   run_mode=gimpfu.RUN_INTERACTIVE)

            pdb.gimp_image_resize_to_layers(temp_image)
            pdb.gimp_layer_flatten(temp_layer)

            pdb.gimp_image_select_contiguous_color(
                temp_image, gimpfu.CHANNEL_OP_REPLACE, temp_layer, 0, 0
            )
            pdb.gimp_selection_invert(temp_image)
            bounds = pdb.gimp_selection_bounds(temp_image)
            sizex = bounds[3] - bounds[1]
            sizey = bounds[4] - bounds[2]
            pdb.gimp_selection_none(temp_image)
            pdb.gimp_image_crop(temp_image, sizex, sizey, bounds[1], bounds[2])

            if (sq_crop and sizex != sizey
                    and pdb.gimp_procedural_db_proc_exists('script_fu_addborder')):
                if sizex > sizey:
                    dx = 0
                    dy = (sizex - sizey) * 0.5
                else:
                    dx = (sizey - sizex) * 0.5
                    dy = 0

                pdb.script_fu_addborder(temp_image, temp_layer, dx, dy, bg_color, 0)
                pdb.gimp_image_raise_item_to_top(temp_image, temp_layer)
                pdb.gimp_image_merge_visible_layers(temp_image, gimpfu.EXPAND_AS_NECESSARY)
                temp_layer = pdb.gimp_image_get_active_layer(temp_image)
        else:
            temp_image = image
            pdb.gimp_image_undo_disable(temp_image)
            temp_layer = pdb.gimp_image_get_active_layer(temp_image)

            if sq_crop:
                c_x = 0.5 * (bounds[1] + bounds[3])
                c_y = 0.5 * (bounds[2] + bounds[4])
                hl = padding + max(sizex, sizey) * 0.5
                sel_x = c_x - hl
                sel_y = c_y - hl
                sel_w = sel_h = 2 * hl
            else:
                sel_x = bounds[1]
                sel_y = bounds[2]
                sel_w = sizex
                sel_h = sizey

            pdb.gimp_image_select_rectangle(
                temp_image, gimpfu.CHANNEL_OP_REPLACE,
                sel_x, sel_y, sel_w, sel_h
            )
            buffname = pdb.gimp_edit_named_copy(drawable, buffname)
            temp_image = pdb.gimp_edit_named_paste_as_new(buffname)
            temp_layer = pdb.gimp_image_get_active_layer(temp_image)

        if padding and pdb.gimp_procedural_db_proc_exists('script_fu_addborder'):
            pdb.script_fu_addborder(temp_image, temp_layer, padding, padding, bg_color, 0)
            pdb.gimp_image_merge_visible_layers(temp_image, gimpfu.EXPAND_AS_NECESSARY)
            temp_layer = pdb.gimp_image_get_active_layer(temp_image)

        pdb.gimp_image_undo_enable(temp_image)
        temp_display = pdb.gimp_display_new(temp_image)

        extracted += 1

        filename = new_fullpath_tpl % (extracted, )
        pdb.gimp_image_set_resolution(temp_image, save_dpi, save_dpi)
        if img_ext == 'jpg':
            pdb.file_jpeg_save(
                temp_image, temp_layer, filename, filename,
                jpg_qual, 0.1, 1, 1, '', 2, 0, 0, 1
            )
        else:
            pdb.gimp_file_save(temp_image, temp_layer, filename, filename)

        if autoclose:
            pdb.gimp_display_delete(temp_display)

        if extracted >= limit:
            break

    pdb.gimp_progress_set_text('Extracted %d images' % (extracted, ))

    pdb.gimp_image_remove_vectors(image, newpath)
    pdb.gimp_selection_none(image)

    pdb.gimp_image_undo_enable(image)
    pdb.gimp_progress_end()
    pdb.gimp_displays_flush()
    gimp.context_pop()

    return extracted

gimpfu.register(
    "photo-cutter",
    "Cut out photos from scanned image",
    "Find and cut out parts of an image. Will also try to deskew them (deskew plugin required). "\
        "Useful for multiple photos scanned at once.",
    "Dmitriy Geels", "Dmitriy Geels", "2018",
    "_Cut out photos",
    "RGB*,GRAY*", # type of image it works on (*, RGB, RGB*, RGBA, GRAY etc...)
    [ # pylint: disable=C0301,C0326
        (gimpfu.PF_IMAGE,    "image",        "Current image",            None),
        (gimpfu.PF_DRAWABLE, "drawable",     "Input layer",              None),
        (gimpfu.PF_SPINNER,  "limit",        "Max number of items",      10, (1, 100, 1)),
        (gimpfu.PF_SPINNER,  "sl_thresh",    "Selection Threshold",      25, (0, 255, 1)),
        (gimpfu.PF_SPINNER,  "sz_thresh",    "Size Threshold",           100, (0, 2000, 10)),
        (gimpfu.PF_TOGGLE,   "bg_manual",    "Manually set background colour", False),
        (gimpfu.PF_COLOR,    "bg_color",     "Pick background colour",   (255, 255, 255)),
        (gimpfu.PF_OPTION,   "bg_corner",    "Auto-background sample corner", 0, ("Top Left", "Top Right", "Bottom Left", "Bottom Right")),
        (gimpfu.PF_SPINNER,  "bg_x",         "Auto-background sample x-offset", 25, (5, 100, 1)),
        (gimpfu.PF_SPINNER,  "bg_y",         "Auto-background sample y-offset", 25, (5, 100, 1)),
        (gimpfu.PF_SPINNER,  "padding",      "Draw border (px)",         0, (0, 100, 1)),
        (gimpfu.PF_TOGGLE,   "deskew",       "Run Deskew plugin if available", True),
        (gimpfu.PF_TOGGLE,   "sq_crop",      "Force square crop",        False),
        (gimpfu.PF_TOGGLE,   "autoclose",    "Autoclose sub-images",     True),
        (gimpfu.PF_TOGGLE,   "save_same",    "Save output to the same directory", True),
        (gimpfu.PF_DIRNAME,  "save_dir",     "Target directory (if not same)", ""),
        (gimpfu.PF_OPTION,   "save_ftype",   "Save File Type",           0, ("jpg", "png", "tiff")),
        (gimpfu.PF_SPINNER,  "save_dpi",     "Save DPI",                 300, (0, 1200, 10)),
        (gimpfu.PF_SPINNER,  "jpg_qual",     "JPG Quality",              0.8, (0.1, 1.0, 0.05)),
        (gimpfu.PF_STRING,   "save_suffix",  "Save File suffix",         "Crop")
    ], # pylint: enable=C0301,C0326
    [
        (gimpfu.PF_INT, 'extracted', 'extracted images count')
    ],
    cutter_single_image,
    menu="<Image>/Tools/Scan c_utter")  # second item is menu location

def cutter_batch_images(
        src_dir, src_ftype,
        limit, sl_thresh, sz_thresh,
        bg_manual, bg_color, bg_corner, bg_x, bg_y,
        padding, deskew, sq_crop,
        save_same, save_dir, save_ftype, save_dpi, jpg_qual, save_suffix
    ):
    ftype_match = {
        'jpg': '\.[jJ][pP][eE]?[gG]$',
        'bmp': '\.[bB][mM][pP]$',
        'png': '\.[pP][mnNM][gG]$',
        'tif': '\.[tT][iI][fF][fF]?$',
    }
    fn_match = re.compile(ftype_match.get(src_ftype, 'jpg'))
    for fn in os.listdir(src_dir):
        if not os.path.isfile(fn) or not fn_match.search(fn):
            continue
        pdb.gimp_progress_set_text('Processing %s...' % (fn, ))
        image = pdb.gimp_file_load(fn, fn)
        if not image:
            pdb.gimp_progress_set_text('Error loading %s...' % (fn, ))
            continue

        cutter_single_image(
            image, image.active_layer,
            limit, sl_thresh, sz_thresh,
            bg_manual, bg_color, bg_corner, bg_x, bg_y,
            padding, deskew, sq_crop, True,
            save_same, save_dir, save_ftype, save_dpi, jpg_qual, save_suffix
        )

        pdb.gimp_image_delete(image)

    pdb.gimp_progress_end()

gimpfu.register(
    "batch-photo-cutter",
    "Cut out photos from scanned image",
    "Find and cut out parts of an image. Will also try to deskew them (deskew plugin required). "\
        "Useful for multiple photos scanned at once.",
    "Dmitriy Geels", "Dmitriy Geels", "2018",
    "_Batch cut out photos...",
    "",
    [ # pylint: disable=C0301,C0326
        (gimpfu.PF_DIRNAME,  "src_dir",      "Source directory",         ""),
        (gimpfu.PF_OPTION,   "src_ftype",    "File Type",                0, ("jpg", "png", "tiff")),
        (gimpfu.PF_SPINNER,  "limit",        "Max number of items",      1, (1, 100, 1)),
        (gimpfu.PF_SPINNER,  "sl_thresh",    "Selection Threshold",      25, (0, 255, 1)),
        (gimpfu.PF_SPINNER,  "sz_thresh",    "Size Threshold",           100, (0, 2000, 10)),
        (gimpfu.PF_TOGGLE,   "bg_manual",    "Manually set background colour", False),
        (gimpfu.PF_COLOR,    "bg_color",     "Pick background colour",   (255, 255, 255)),
        (gimpfu.PF_OPTION,   "bg_corner",    "Auto-background sample corner", 0, ("Top Left", "Top Right", "Bottom Left", "Bottom Right")),
        (gimpfu.PF_SPINNER,  "bg_x",         "Auto-background sample x-offset", 25, (5, 100, 1)),
        (gimpfu.PF_SPINNER,  "bg_y",         "Auto-background sample y-offset", 25, (5, 100, 1)),
        (gimpfu.PF_SPINNER,  "padding",      "Draw border (px)",         0, (0, 100, 1)),
        (gimpfu.PF_TOGGLE,   "deskew",       "Run Deskew plugin if available", True),
        (gimpfu.PF_TOGGLE,   "sq_crop",      "Force square crop",        False),
        (gimpfu.PF_TOGGLE,   "save_same",    "Save output to the same directory", True),
        (gimpfu.PF_DIRNAME,  "save_dir",     "Target directory (if not same)", ""),
        (gimpfu.PF_OPTION,   "save_ftype",   "Save File Type",           0, ("jpg", "png", "tiff")),
        (gimpfu.PF_SPINNER,  "save_dpi",     "Save DPI",                 300, (0, 1200, 10)),
        (gimpfu.PF_SPINNER,  "jpg_qual",     "JPG Quality",              0.8, (0.1, 1.0, 0.05)),
        (gimpfu.PF_STRING,   "save_suffix",  "Save File suffix",         "Crop")
    ], # pylint: enable=C0301,C0326
    [
        (gimpfu.PF_INT, 'extracted', 'extracted images count')
    ],
    cutter_batch_images,
    menu="<Toolbox>/Tools/Scan c_utter")  # second item is menu location

gimpfu.main()
