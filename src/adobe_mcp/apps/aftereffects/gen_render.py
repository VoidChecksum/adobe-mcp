"""Generative render pipeline — create procedural animations in After Effects.

Takes generative expression code, creates a comp with a base layer, applies the
expression to a target property, adds effects/filters, and optionally renders.
Supports seamless looping via loopOut or time-modulo wrapping.
"""

import json

from adobe_mcp.engine import _async_run_jsx
from adobe_mcp.apps.aftereffects.models import AeGenRenderInput


def _build_gen_render_jsx(params: AeGenRenderInput) -> str:
    """Build the JSX script for the full generative render pipeline.

    Constructs a single JSX script that:
    1. Creates a new comp at the specified dimensions/duration/fps
    2. Creates the base layer (solid, shape, or text)
    3. Applies the generative expression to the target property
    4. Wraps the expression with loopOut if loop=True
    5. Applies each filter/effect from the filters list
    6. Sets effect parameters from filter_params
    7. Optionally adds to render queue with output module

    Returns the complete JSX code string ready for execution.
    """
    # -- Background color: normalize [r,g,b] 0-255 to [r,g,b] 0-1 for AE
    bg = params.bg_color or [0, 0, 0]
    bg_r = max(0, min(255, int(bg[0]))) / 255.0
    bg_g = max(0, min(255, int(bg[1]))) / 255.0
    bg_b = max(0, min(255, int(bg[2]))) / 255.0

    # -- Layer color: normalize [r,g,b] 0-255 to [r,g,b] 0-1 for AE solid
    lc = params.layer_color or [255, 255, 255]
    lc_r = max(0, min(255, int(lc[0]))) / 255.0
    lc_g = max(0, min(255, int(lc[1]))) / 255.0
    lc_b = max(0, min(255, int(lc[2]))) / 255.0

    # -- Escape the expression code for embedding in JSX string literal
    # AE expressions can contain quotes, backslashes, and newlines
    escaped_code = (
        params.code
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )

    # -- Build the expression with optional loopOut wrapping
    if params.loop:
        # Append loopOut to make the expression cycle seamlessly.
        # If the user's code already contains loopOut, don't double-wrap.
        if "loopOut" in params.code or "loopIn" in params.code:
            final_expr = escaped_code
        else:
            # Wrap: apply the user expression, then add loopOut at the end
            final_expr = escaped_code + "\\n" + "loopOut('cycle');"
    else:
        final_expr = escaped_code

    # -- Map property_target to the AE property path
    # Common shortcuts map to full Transform property paths
    property_map = {
        "position": "Transform.Position",
        "scale": "Transform.Scale",
        "rotation": "Transform.Rotation",
        "opacity": "Transform.Opacity",
        "anchor": "Transform.Anchor Point",
    }
    prop_target = property_map.get(params.property_target.lower(), params.property_target)

    # Build the JSX property accessor chain from dot-separated path
    # e.g. "Transform.Position" -> .property("Transform").property("Position")
    prop_parts = prop_target.split(".")
    prop_chain = "".join([f'.property("{p}")' for p in prop_parts])

    # -- Escape comp name for JSX string embedding
    comp_name_escaped = params.comp_name.replace('"', '\\"')

    # -- Build layer creation JSX based on layer_type
    if params.layer_type == "shape":
        layer_jsx = f"""
var layer = comp.layers.addShape();
layer.name = "GenLayer";
"""
    elif params.layer_type == "text":
        layer_jsx = """
var layer = comp.layers.addText("Gen");
layer.name = "GenLayer";
"""
    else:
        # Default: solid layer
        layer_jsx = f"""
var layer = comp.layers.addSolid(
    [{lc_r}, {lc_g}, {lc_b}],
    "GenLayer",
    comp.width,
    comp.height,
    1
);
"""

    # -- Build effects application JSX
    effects_jsx = ""
    if params.filters:
        for effect_name in params.filters:
            eff_escaped = effect_name.replace('"', '\\"')
            effects_jsx += f"""
try {{
    var eff = layer.property("Effects").addProperty("{eff_escaped}");
    appliedEffects.push(eff.name);
}} catch(e) {{
    failedEffects.push({{ name: "{eff_escaped}", error: e.toString() }});
}}
"""

    # -- Build effect parameter setting JSX
    params_jsx = ""
    if params.filter_params:
        for effect_name, effect_settings in params.filter_params.items():
            eff_escaped = effect_name.replace('"', '\\"')
            if isinstance(effect_settings, dict):
                for param_name, param_value in effect_settings.items():
                    param_escaped = param_name.replace('"', '\\"')
                    # Determine how to set the value based on type
                    if isinstance(param_value, (list, tuple)):
                        value_jsx = json.dumps(param_value)
                    elif isinstance(param_value, bool):
                        value_jsx = "true" if param_value else "false"
                    elif isinstance(param_value, (int, float)):
                        value_jsx = str(param_value)
                    else:
                        value_jsx = f'"{str(param_value)}"'

                    params_jsx += f"""
try {{
    layer.property("Effects").property("{eff_escaped}").property("{param_escaped}").setValue({value_jsx});
}} catch(e) {{
    failedParams.push({{ effect: "{eff_escaped}", param: "{param_escaped}", error: e.toString() }});
}}
"""

    # -- Build render queue JSX (optional)
    render_jsx = ""
    if params.render and params.output_path:
        output_path = params.output_path.replace("\\", "/")

        # Map output format to AE output module template names
        # These are the standard AE output module presets
        format_templates = {
            "mp4": "H.264 - Match Render Settings - 15 Mbps",
            "mov": "Lossless",
            "gif": "Animated GIF",
        }
        om_template = format_templates.get(params.output_format, "")

        render_jsx = f"""
// -- Add to render queue
var rqItem = app.project.renderQueue.items.add(comp);
var om = rqItem.outputModule(1);
om.file = new File("{output_path}");
"""
        # Try to apply the output module template; if the exact name doesn't
        # exist in the user's AE install, fall back to whatever default is set
        if om_template:
            om_escaped = om_template.replace('"', '\\"')
            render_jsx += f"""
try {{
    om.applyTemplate("{om_escaped}");
}} catch(e) {{
    // Template name may differ across AE versions; use default
    result.renderWarning = "Output module template '{om_escaped}' not found, using default";
}}
"""
        render_jsx += """
app.project.renderQueue.render();
result.rendered = true;
"""

    # -- Assemble the complete JSX script
    jsx = f"""
// -- Generative Render Pipeline --
// Track results for structured output
var appliedEffects = [];
var failedEffects = [];
var failedParams = [];
var result = {{
    rendered: false,
    renderWarning: null
}};

// 1. Create composition
var comp = app.project.items.addComp(
    "{comp_name_escaped}",
    {params.width},
    {params.height},
    1,
    {params.duration},
    {params.fps}
);

// Set background color
comp.bgColor = [{bg_r}, {bg_g}, {bg_b}];

// 2. Create the base layer
{layer_jsx}

// 3. Apply generative expression to target property
try {{
    var prop = layer{prop_chain};
    prop.expression = "{final_expr}";
    result.expressionApplied = true;
    result.propertyTarget = "{prop_target}";
}} catch(e) {{
    result.expressionApplied = false;
    result.expressionError = e.toString();
}}

// 4. Apply effects/filters
{effects_jsx}

// 5. Set effect parameters
{params_jsx}

// 6. Build result
result.comp = {{
    name: comp.name,
    width: comp.width,
    height: comp.height,
    duration: comp.duration,
    fps: comp.frameRate,
    numLayers: comp.numLayers
}};
result.layer = {{
    name: layer.name,
    type: "{params.layer_type}"
}};
result.appliedEffects = appliedEffects;
if (failedEffects.length > 0) result.failedEffects = failedEffects;
if (failedParams.length > 0) result.failedParams = failedParams;
result.loop = {"true" if params.loop else "false"};

{render_jsx}

// 7. Open comp in viewer so user can see it
comp.openInViewer();

JSON.stringify(result, null, 2);
"""
    return jsx


def register(mcp):
    """Register the adobe_ae_gen_render tool."""

    @mcp.tool(
        name="adobe_ae_gen_render",
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def adobe_ae_gen_render(params: AeGenRenderInput) -> str:
        """Generate and render procedural animation in After Effects.

        Creates a comp, adds a base layer (solid/shape/text), applies generative
        expression code to the target property (position, scale, rotation, opacity,
        or any custom property path), applies effects/filters with parameters, and
        optionally renders to mp4/mov/gif. Supports seamless looping.
        """
        # Validate: render=True requires output_path
        if params.render and not params.output_path:
            return "Error: output_path is required when render=True"

        # Validate: layer_type is one of the supported types
        if params.layer_type not in ("solid", "shape", "text"):
            return f"Error: layer_type must be 'solid', 'shape', or 'text', got '{params.layer_type}'"

        # Validate: output_format is one of the supported formats
        if params.output_format not in ("mp4", "mov", "gif"):
            return f"Error: output_format must be 'mp4', 'mov', or 'gif', got '{params.output_format}'"

        jsx = _build_gen_render_jsx(params)

        # Use longer timeout for render operations (up to 10 minutes)
        timeout = 600 if params.render else 120
        result = await _async_run_jsx("aftereffects", jsx, timeout=timeout)
        return result["stdout"] if result["success"] else f"Error: {result['stderr']}"
