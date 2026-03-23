"""After Effects tools — 7 tools split by feature.

Registration chain:
    apps/__init__.py -> aftereffects/__init__.py -> {comp, layer, property, expression, effect, render, gen_render}.py
"""

from adobe_mcp.apps.aftereffects.comp import register as _reg_comp
from adobe_mcp.apps.aftereffects.layer import register as _reg_layer
from adobe_mcp.apps.aftereffects.property import register as _reg_property
from adobe_mcp.apps.aftereffects.expression import register as _reg_expression
from adobe_mcp.apps.aftereffects.effect import register as _reg_effect
from adobe_mcp.apps.aftereffects.render import register as _reg_render
from adobe_mcp.apps.aftereffects.gen_render import register as _reg_gen_render


def register_aftereffects_tools(mcp):
    """Register all 7 After Effects tools."""
    _reg_comp(mcp)
    _reg_layer(mcp)
    _reg_property(mcp)
    _reg_expression(mcp)
    _reg_effect(mcp)
    _reg_render(mcp)
    _reg_gen_render(mcp)
