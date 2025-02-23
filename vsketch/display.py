import io
import logging
import random
import sys
from typing import List, Optional, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import vpype as vp

from .environment import COLAB, JUPYTERLAB, get_svg_pan_zoom_url

try:
    # noinspection PyPackageRequirements
    import IPython
except ModuleNotFoundError:
    pass

COLORS = [
    (0, 0, 1),
    (0, 0.5, 0),
    (1, 0, 0),
    (0, 0.75, 0.75),
    (0, 1, 0),
    (0.75, 0, 0.75),
    (0.75, 0.75, 0),
    (0, 0, 0),
]


def display_matplotlib(
    document: vp.Document,
    page_size: Tuple[float, float] = None,
    center: bool = False,
    show_axes: bool = True,
    show_grid: bool = False,
    show_pen_up: bool = False,
    colorful: bool = False,
    unit: str = "px",
    fig_size: Tuple[float, float] = None,
) -> None:
    scale = 1 / vp.convert_length(unit)

    if fig_size:
        plt.figure(figsize=fig_size)
    plt.cla()

    # draw page
    if page_size is not None:
        w = page_size[0] * scale
        h = page_size[1] * scale
        dw = 10 * scale
        plt.fill(
            np.array([w, w + dw, w + dw, dw, dw, w]),
            np.array([dw, dw, h + dw, h + dw, h, h]),
            "k",
            alpha=0.3,
        )
        plt.plot(np.array([0, 1, 1, 0, 0]) * w, np.array([0, 0, 1, 1, 0]) * h, "-k", lw=0.25)

    # compute offset
    offset = complex(0, 0)
    if center and page_size:
        bounds = document.bounds()
        if bounds is not None:
            offset = complex(
                (page_size[0] - (bounds[2] - bounds[0])) / 2.0 - bounds[0],
                (page_size[1] - (bounds[3] - bounds[1])) / 2.0 - bounds[1],
            )
    offset_ndarr = np.array([offset.real, offset.imag])

    # plot all layers
    color_idx = 0
    collections = {}
    for layer_id, lc in document.layers.items():
        if colorful:
            color: Union[Tuple[float, float, float], List[Tuple[float, float, float]]] = (
                COLORS[color_idx:] + COLORS[:color_idx]
            )
            color_idx += len(lc)
        else:
            color = COLORS[color_idx]
            color_idx += 1
        if color_idx >= len(COLORS):
            color_idx = color_idx % len(COLORS)

        # noinspection PyUnresolvedReferences
        layer_lines = matplotlib.collections.LineCollection(
            (vp.as_vector(line + offset) * scale for line in lc),
            color=color,
            lw=1,
            alpha=0.5,
            label=str(layer_id),
        )
        collections[layer_id] = [layer_lines]
        plt.gca().add_collection(layer_lines)

        if show_pen_up:
            # noinspection PyUnresolvedReferences
            pen_up_lines = matplotlib.collections.LineCollection(
                (
                    (
                        (vp.as_vector(lc[i])[-1] + offset_ndarr) * scale,
                        (vp.as_vector(lc[i + 1])[0] + offset_ndarr) * scale,
                    )
                    for i in range(len(lc) - 1)
                ),
                color=(0, 0, 0),
                lw=0.5,
                alpha=0.5,
            )
            collections[layer_id].append(pen_up_lines)
            plt.gca().add_collection(pen_up_lines)

    plt.gca().invert_yaxis()
    plt.axis("equal")
    plt.margins(0, 0)

    if show_axes or show_grid:
        plt.axis("on")
        plt.xlabel(f"[{unit}]")
        plt.ylabel(f"[{unit}]")
    else:
        plt.axis("off")
    if show_grid:
        plt.grid("on")

    plt.show()


def display_ipython(
    document: vp.Document,
    page_size: Optional[Tuple[float, float]],
    center: bool = False,
    show_pen_up: bool = False,
    color_mode: str = "layer",
) -> None:
    """Implements a SVG previsualisation with pan/zoom support for IPython.

    If page_size is provided, a page is displayed and the sketch is laid out on it. Otherwise
    the sketch is displayed using its intrinsic boundaries.
    """
    if "IPython" not in sys.modules:
        raise RuntimeError("IPython display cannot be used outside of IPython")

    svg_io = io.StringIO()
    vp.write_svg(
        svg_io,
        document,
        page_size if page_size is not None else (0, 0),
        center,
        show_pen_up=show_pen_up,
        color_mode=color_mode,
    )

    MARGIN = 10

    if page_size is None:
        bounds = document.bounds()
        if bounds:
            svg_width = bounds[2] - bounds[0]
            svg_height = bounds[3] - bounds[1]
        else:
            svg_width = 0
            svg_height = 0
    else:
        svg_width = page_size[0]
        svg_height = page_size[1]

    page_boundaries = f"""
        <polygon points="{svg_width},{MARGIN}
            {svg_width + MARGIN},{MARGIN}
            {svg_width + MARGIN},{svg_height + MARGIN}
            {MARGIN},{svg_height + MARGIN}
            {MARGIN},{svg_height}
            {svg_width},{svg_height}"
            style="fill:black;stroke:none;opacity:0.3;" />
        <rect width="{svg_width}" height="{svg_height}"
            style="fill:none;stroke-width:1;stroke:rgb(0,0,0)" />
    """

    svg_margin = MARGIN if page_size is not None else 0
    svg_id = f"svg_display_{random.randint(0, 10000)}"

    IPython.display.display_html(
        f"""<div id="container" style="width: 80%; height: {svg_height + svg_margin}px;">
            <svg id="{svg_id}" width="{svg_width + svg_margin}px"
                    height={svg_height + svg_margin}
                    viewBox="0 0 {svg_width + svg_margin} {svg_height + svg_margin}">
                {page_boundaries if page_size is not None else ""}
                {svg_io.getvalue()}
            </svg>
        </div>
        <script src="{get_svg_pan_zoom_url()}"></script>
        <script>
            svgPanZoom('#{svg_id}', {{
                zoomEnabled: true,
                controlIconsEnabled: true,
                center: true,
                zoomScaleSensitivity: 0.3,
                contain: true,
            }});
          </script>
        """,
        raw=True,
    )


def display(
    document: vp.Document,
    page_size: Optional[Tuple[float, float]],
    center: bool = False,
    show_axes: bool = True,
    show_grid: bool = False,
    show_pen_up: bool = False,
    color_mode: str = "layer",
    unit: str = "px",
    mode: Optional[str] = None,
    fig_size: Tuple[float, float] = None,
) -> None:
    """Display a layout with vector data using the best method given the environment.

    Supported modes:

        "matplotlib": use matplotlib to render the preview
        "ipython": use SVG with zoom/pan capability (requires IPython)

    Note: all options are not necessarily implemented by all display modes.

    Args:
        document: the document to display
        page_size: size of the page in pixels
        center: if True, the geometries are centered on the page
        show_axes: if True, display axes
        show_grid: if True, display a grid
        show_pen_up: if True, display pen-up trajectories
        color_mode: "none" (everything is black and white), "layer" (one color per layer), or
            "path" (one color per path)
        unit: display unit
        mode: if provided, force a specific display mode
        fig_size: if provided, set the matplotlib figure size
    """

    if mode is None:
        if COLAB or JUPYTERLAB:
            mode = "ipython"
        else:
            mode = "matplotlib"

    if mode == "ipython":
        if show_axes:
            logging.warning("show_axis is not supported by the IPython display mode")

        if show_grid:
            logging.warning("show_grid is not supported by the IPython display mode")

        if unit != "px":
            logging.warning("custom units are not supported by the IPython display mode")

        if fig_size is not None:
            logging.warning("setting fig_size is not supported by the IPython display mode")

        display_ipython(
            document, page_size, center, show_pen_up=show_pen_up, color_mode=color_mode
        )
    elif mode == "matplotlib":
        display_matplotlib(
            document,
            page_size,
            center=center,
            show_axes=show_axes,
            show_grid=show_grid,
            show_pen_up=show_pen_up,
            colorful=(color_mode == "path"),
            unit=unit,
            fig_size=fig_size,
        )
    else:
        raise ValueError(f"unsupported display mode: {mode}")
