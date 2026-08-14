from __future__ import annotations

import array

from arcade.types import Color, Rect, RGBOrA255
from arcade.window_commands import get_window

V = """
#version 330

uniform WindowBlock {
    mat4 projection;
    mat4 view;
} window;

// [w, h, tilt]
uniform vec3 shape;

in vec2 in_vert;
in vec2 in_instance_pos;

out vec2 vs_uv;

void main() {
    float angle = radians(shape.z);
    mat2 rot = mat2(
        cos(angle), -sin(angle),
        sin(angle),  cos(angle)
    );
    // vec2 size = shape.xy / 2.0;
    mat4 mvp = window.projection * window.view;
    vec2 pos = in_instance_pos + (rot * (in_vert * shape.xy));
    gl_Position = mvp * vec4(pos, 0.0, 1.0);
    vs_uv = in_vert + 0.5;
}
"""

F = """
#version 330
uniform vec4 colora;
uniform vec4 colorb;

in vec2 vs_uv;

out vec4 fs_color;

//////////////////////////////////////////////////////////////////////
// sRGB color transform and inverse from
// https://bottosson.github.io/posts/colorwrong/#what-can-we-do%3F

vec3 srgb_from_linear_srgb(vec3 x) {

    vec3 xlo = 12.92*x;
    vec3 xhi = 1.055 * pow(x, vec3(0.4166666666666667)) - 0.055;

    return mix(xlo, xhi, step(vec3(0.0031308), x));

}

vec3 linear_srgb_from_srgb(vec3 x) {

    vec3 xlo = x / 12.92;
    vec3 xhi = pow((x + 0.055)/(1.055), vec3(2.4));

    return mix(xlo, xhi, step(vec3(0.04045), x));

}

//////////////////////////////////////////////////////////////////////
// oklab transform and inverse from
// https://bottosson.github.io/posts/oklab/


const mat3 fwdA = mat3(1.0, 1.0, 1.0,
                       0.3963377774, -0.1055613458, -0.0894841775,
                       0.2158037573, -0.0638541728, -1.2914855480);

const mat3 fwdB = mat3(4.0767245293, -1.2681437731, -0.0041119885,
                       -3.3072168827, 2.6093323231, -0.7034763098,
                       0.2307590544, -0.3411344290,  1.7068625689);

const mat3 invB = mat3(0.4121656120, 0.2118591070, 0.0883097947,
                       0.5362752080, 0.6807189584, 0.2818474174,
                       0.0514575653, 0.1074065790, 0.6302613616);

const mat3 invA = mat3(0.2104542553, 1.9779984951, 0.0259040371,
                       0.7936177850, -2.4285922050, 0.7827717662,
                       -0.0040720468, 0.4505937099, -0.8086757660);

vec3 oklab_from_linear_srgb(vec3 c) {

    vec3 lms = invB * c;

    return invA * (sign(lms)*pow(abs(lms), vec3(0.3333333333333)));

}

vec3 linear_srgb_from_oklab(vec3 c) {

    vec3 lms = fwdA * c;

    return fwdB * (lms * lms * lms);

}

//////////////////////////////////////////////////////////////////////


void main() {
    vec4 a = vec4(oklab_from_linear_srgb(linear_srgb_from_srgb(colora.rgb)), colora.a);
    vec4 b = vec4(oklab_from_linear_srgb(linear_srgb_from_srgb(colorb.rgb)), colorb.a);

    vec4 m = mix(b, a, vs_uv.y);
    fs_color = vec4(srgb_from_linear_srgb(linear_srgb_from_oklab(m.rgb)), m.a);
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
    program = ctx.program(vertex_shader=V, fragment_shader=F)
    geometry = ctx.shape_rectangle_filled_unbuffered_geometry
    buffer = ctx.shape_rectangle_filled_unbuffered_buffer  # type: ignore

    ctx.enable(ctx.BLEND)

    # Pass data to the shader
    program["colora"] = Color.from_iterable(color_a).normalized
    program["colorb"] = Color.from_iterable(color_b).normalized
    program["shape"] = rect.width, rect.height, tilt_angle
    buffer.orphan()
    buffer.write(data=array.array("f", (rect.x, rect.y)))

    geometry.render(program, instances=1)

    ctx.disable(ctx.BLEND)
