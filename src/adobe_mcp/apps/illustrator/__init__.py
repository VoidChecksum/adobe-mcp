"""Illustrator tools — 35 tools split by feature.

Registration chain:
    apps/__init__.py -> illustrator/__init__.py -> {new_document, shapes, text, paths, export, layers, modify, inspect, image_trace, analyze_reference, reference_underlay, vtrace, anchor_edit, silhouette, auto_correct, proportion_grid, style_transfer, shape_recipes, contour_to_path, smart_shape, bezier_optimize, curve_fit, artboard_from_ref, path_boolean, symmetry, layer_auto_organize, group_and_name, color_sampler, stroke_profiles, path_offset, path_weld, snap_to_grid, undo_checkpoint, reference_crop, drawing_orchestrator}.py
"""

from adobe_mcp.apps.illustrator.new_document import register as _reg_new_document
from adobe_mcp.apps.illustrator.shapes import register as _reg_shapes
from adobe_mcp.apps.illustrator.text import register as _reg_text
from adobe_mcp.apps.illustrator.paths import register as _reg_paths
from adobe_mcp.apps.illustrator.export import register as _reg_export
from adobe_mcp.apps.illustrator.layers import register as _reg_layers
from adobe_mcp.apps.illustrator.modify import register as _reg_modify
from adobe_mcp.apps.illustrator.inspect import register as _reg_inspect
from adobe_mcp.apps.illustrator.image_trace import register as _reg_image_trace
from adobe_mcp.apps.illustrator.analyze_reference import register as _reg_analyze_reference
from adobe_mcp.apps.illustrator.reference_underlay import register as _reg_reference_underlay
from adobe_mcp.apps.illustrator.vtrace import register as _reg_vtrace
from adobe_mcp.apps.illustrator.anchor_edit import register as _reg_anchor_edit
from adobe_mcp.apps.illustrator.silhouette import register as _reg_silhouette
from adobe_mcp.apps.illustrator.auto_correct import register as _reg_auto_correct
from adobe_mcp.apps.illustrator.proportion_grid import register as _reg_proportion_grid
from adobe_mcp.apps.illustrator.style_transfer import register as _reg_style_transfer
from adobe_mcp.apps.illustrator.shape_recipes import register as _reg_shape_recipes
from adobe_mcp.apps.illustrator.contour_to_path import register as _reg_contour_to_path
from adobe_mcp.apps.illustrator.smart_shape import register as _reg_smart_shape
from adobe_mcp.apps.illustrator.bezier_optimize import register as _reg_bezier_optimize
from adobe_mcp.apps.illustrator.curve_fit import register as _reg_curve_fit
from adobe_mcp.apps.illustrator.artboard_from_ref import register as _reg_artboard_from_ref
from adobe_mcp.apps.illustrator.path_boolean import register as _reg_path_boolean
from adobe_mcp.apps.illustrator.symmetry import register as _reg_symmetry
from adobe_mcp.apps.illustrator.layer_auto_organize import register as _reg_layer_auto_organize
from adobe_mcp.apps.illustrator.group_and_name import register as _reg_group_and_name
from adobe_mcp.apps.illustrator.color_sampler import register as _reg_color_sampler
from adobe_mcp.apps.illustrator.stroke_profiles import register as _reg_stroke_profiles
from adobe_mcp.apps.illustrator.path_offset import register as _reg_path_offset
from adobe_mcp.apps.illustrator.path_weld import register as _reg_path_weld
from adobe_mcp.apps.illustrator.snap_to_grid import register as _reg_snap_to_grid
from adobe_mcp.apps.illustrator.undo_checkpoint import register as _reg_undo_checkpoint
from adobe_mcp.apps.illustrator.reference_crop import register as _reg_reference_crop
from adobe_mcp.apps.illustrator.drawing_orchestrator import register as _reg_drawing_orchestrator


def register_illustrator_tools(mcp):
    """Register all 35 Illustrator tools."""
    _reg_new_document(mcp)
    _reg_shapes(mcp)
    _reg_text(mcp)
    _reg_paths(mcp)
    _reg_export(mcp)
    _reg_layers(mcp)
    _reg_modify(mcp)
    _reg_inspect(mcp)
    _reg_image_trace(mcp)
    _reg_analyze_reference(mcp)
    _reg_reference_underlay(mcp)
    _reg_vtrace(mcp)
    _reg_anchor_edit(mcp)
    _reg_silhouette(mcp)
    _reg_auto_correct(mcp)
    _reg_proportion_grid(mcp)
    _reg_style_transfer(mcp)
    _reg_shape_recipes(mcp)
    _reg_contour_to_path(mcp)
    _reg_smart_shape(mcp)
    _reg_bezier_optimize(mcp)
    _reg_curve_fit(mcp)
    _reg_artboard_from_ref(mcp)
    _reg_path_boolean(mcp)
    _reg_symmetry(mcp)
    _reg_layer_auto_organize(mcp)
    _reg_group_and_name(mcp)
    _reg_color_sampler(mcp)
    _reg_stroke_profiles(mcp)
    _reg_path_offset(mcp)
    _reg_path_weld(mcp)
    _reg_snap_to_grid(mcp)
    _reg_undo_checkpoint(mcp)
    _reg_reference_crop(mcp)
    _reg_drawing_orchestrator(mcp)
