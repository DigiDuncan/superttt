from __future__ import annotations

import array

from arcade.types import Color, Rect, RGBOrA255
from arcade.window_commands import get_window

V = """
#version 330

in vec2 in_vert;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

G = """
#version 330

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

uniform WindowBlock {
    mat4 projection;
    mat4 view;
} window;

// [w, h, tilt]
uniform vec3 shape;

out vec2 gs_uv;

void main() {
    // Get center of the circle
    vec2 center = gl_in[0].gl_Position.xy;

    // Calculate rotation/tilt
    float angle = radians(shape.z);
    mat2 rot = mat2(
        cos(angle), -sin(angle),
        sin(angle),  cos(angle)
    );
    vec2 size = shape.xy / 2.0;

    // Emit quad as triangle strip
    vec2 p1 = rot * vec2(-size.x,  size.y);
    vec2 p2 = rot * vec2(-size.x, -size.y);
    vec2 p3 = rot * vec2( size.x,  size.y);
    vec2 p4 = rot * vec2( size.x, -size.y);

    gl_Position = window.projection * window.view * vec4(p1 + center, 0.0, 1.0);
    gs_uv = vec2(0.0, 1.0);
    EmitVertex();
    gl_Position = window.projection * window.view * vec4(p2 + center, 0.0, 1.0);
    gs_uv = vec2(0.0, 0.0); 
    EmitVertex();
    gl_Position = window.projection * window.view * vec4(p3 + center, 0.0, 1.0);
    gs_uv = vec2(1.0, 1.0);
    EmitVertex();
    gl_Position = window.projection * window.view * vec4(p4 + center, 0.0, 1.0);
    gs_uv = vec2(1.0, 0.0);
    EmitVertex();

    EndPrimitive();
}

"""

F = """
#version 330
uniform vec4 colora;
uniform vec4 colorb;

in vec2 gs_uv;

out vec4 fs_color;

#define NEWTON_ITER 1
#define HALLEY_ITER 1

float cbrt( float x )
{
	float y = sign(x) * uintBitsToFloat( floatBitsToUint( abs(x) ) / 3u + 0x2a514067u );

	for( int i = 0; i < NEWTON_ITER; ++i )
    	y = ( 2. * y + x / ( y * y ) ) * .333333333;

    for( int i = 0; i < HALLEY_ITER; ++i )
    {
    	float y3 = y * y * y;
        y *= ( y3 + 2. * x ) / ( 2. * y3 + x );
    }
    
    return y;
}

float gammaToLinear(float c){
  return c >= 0.04045 ? pow((c + 0.055) / 1.055, 2.4) : c / 12.92;
}

// correlary of the first " : "..then switching back" :
float linearToGamma(float c){
  return c >= 0.0031308 ? 1.055 * pow(c, 1 / 2.4) - 0.055 : 12.92 * c;
}

vec3 rgbToOklab(vec3 c) {
  // This is my undersanding: JavaScript canvas and many other virtual and literal devices use gamma-corrected (non-linear lightness) RGB, or sRGB. To convert sRGB values for manipulation in the Oklab color space, you must first convert them to linear RGB. Where Oklab interfaces with RGB it expects and returns linear RGB values. This next step converts (via a function) sRGB to linear RGB for Oklab to use:
  float r = gammaToLinear(c.r); 
  float g = gammaToLinear(c.g);
  float b = gammaToLinear(c.b);
  // This is the Oklab math:
  float l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  float m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  float s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;

  l = cbrt(l); m = cbrt(m); s = cbrt(s);
  return vec3(
    l * +0.2104542553 + m * +0.7936177850 + s * -0.0040720468,
    l * +1.9779984951 + m * -2.4285922050 + s * +0.4505937099,
    l * +0.0259040371 + m * +0.7827717662 + s * -0.8086757660
  );
}

vec3 oklabToSRGB(vec3 c) {
  float l = c.r + c.g * +0.3963377774 + c.b * +0.2158037573;
  float m = c.r + c.g * -0.1055613458 + c.b * -0.0638541728;
  float s = c.r + c.g * -0.0894841775 + c.b * -1.2914855480;
  // The ** operator here cubes; same as l_*l_*l_ in the C++ example:
  l = pow(l, 3.0); m = pow(m, 3.0); s = pow(s, 3.0);
  float r = l * +4.0767416621 + m * -3.3077115913 + s * +0.2309699292;
  float g = l * -1.2684380046 + m * +2.6097574011 + s * -0.3413193965;
  float b = l * -0.0041960863 + m * -0.7034186147 + s * +1.7076147010;
  // Convert linear RGB values returned from oklab math to sRGB for our use before returning them:
  r = linearToGamma(r); g = linearToGamma(g); b = linearToGamma(b);
  // OPTION: clamp r g and b values to the range 0-255; but if you use the values immediately to draw, JavaScript clamps them on use:
  r = clamp(r, 0.0, 1.0); g = clamp(g, 0.0, 1.0); b = clamp(b, 0.0, 1.0);
  return vec3(r, g, b);
}



void main() {
    vec4 a = vec4(rgbToOklab(colora.rgb), colora.a);
    vec4 b = vec4(rgbToOklab(colorb.rgb), colorb.a);

    vec4 m = mix(b, a, gs_uv.y);
    fs_color = vec4(oklabToSRGB(m.rgb), m.a);
}
"""


def draw_rect_gradient(
    rect: Rect, color_a: RGBOrA255, color_b: RGBOrA255, tilt_angle: float = 0
) -> None:
    """
    Draw a filled-in rectangle.

    Args:
        rect:
            The rectangle to draw. a :py:class`~arcade.types.Rect` instance.
        color:
            The fill color as an RGBA :py:class:`tuple`,
            RGB :py:class:`tuple, or :py:class`.Color` instance.
        tilt_angle:
            rotation of the rectangle (clockwise). Defaults to zero.
    """
    # Fail if we don't have a window, context, or right GL abstractions
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_rectangle_filled_unbuffered_program  # type: ignore
    program = ctx.program(vertex_shader=V, geometry_shader=G, fragment_shader=F)
    geometry = ctx.shape_rectangle_filled_unbuffered_geometry
    buffer = ctx.shape_rectangle_filled_unbuffered_buffer  # type: ignore

    ctx.enable(ctx.BLEND)

    # Pass data to the shader
    program["colora"] = Color.from_iterable(color_a).normalized
    program["colorb"] = Color.from_iterable(color_b).normalized
    program["shape"] = rect.width, rect.height, tilt_angle
    buffer.orphan()
    buffer.write(data=array.array("f", (rect.x, rect.y)))

    geometry.render(program, mode=ctx.POINTS, vertices=1)

    ctx.disable(ctx.BLEND)
