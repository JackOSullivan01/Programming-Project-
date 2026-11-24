from pathlib import Path
from io import BytesIO
import importlib
import traceback

import gradio as gr
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager


# Each graph module supplies its own preview and detailed panel.
PANELS = [
    {
        "title": "Investment growth",
        "description": "Explore historical investment performance.",
        "module": "investment_growth_graph",
        "preview": "make_growth_preview",
        "builder": "build_growth_panel"
    },
    {
        "title": "Risk versus return",
        "description": "Compare sector performance and volatility.",
        "module": "risk_return_graph",
        "preview": "make_risk_preview",
        "builder": "build_risk_panel"
    },
    {
        "title": "Industry correlations",
        "description": "Explore how closely sectors move together.",
        "module": "correlation_graph",
        "preview": "make_correlation_preview",
        "builder": "build_correlation_panel"
    },
    {
        "title": "Return distributions",
        "description": "Investigate return patterns and downside risk.",
        "module": "return_dist_graph",
        "preview": "make_distribution_preview",
        "builder": "build_distribution_panel"
    }
]

PROJECT_FOLDER = Path(__file__).resolve().parent


def make_title_banner():
    # Render the header in Python for exact centring without CSS or HTML.
    width, height = 2200, 280
    image = Image.new("RGB", (width, height), "#17283E")
    draw = ImageDraw.Draw(image)
    bold_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    regular_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans")
    )
    title_font = ImageFont.truetype(bold_path, 90)
    subtitle_font = ImageFont.truetype(regular_path, 30)
    draw.text(
        (width / 2, 106), "Industry Performance Explorer",
        font=title_font, fill="#FFFFFF", anchor="mm"
    )
    draw.text(
        (width / 2, 184),
        "Four perspectives on industry performance. Choose an analysis to explore.",
        font=subtitle_font, fill="#CBD9E8", anchor="mm"
    )
    draw.rounded_rectangle(
        (width / 2 - 65, 235, width / 2 + 65, 241),
        radius=3, fill="#35B7AC"
    )
    return image


PREVIEW_HEIGHT = 300
CARD_HEADER_HEIGHT = 82


def make_card_header(title, description):
    # Equal-sized, high-contrast title strips rendered entirely in Python.
    width, height = 1200, 150
    image = Image.new("RGB", (width, height), "#17283E")
    draw = ImageDraw.Draw(image)
    bold = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    regular = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans")
    )
    draw.rectangle((0, 0, 7, height), fill="#19A99D")
    draw.text((35, 50), title, font=ImageFont.truetype(bold, 46),
              fill="white", anchor="lm")
    draw.text((35, 110), description,
              font=ImageFont.truetype(regular, 25),
              fill="#CBD9E8", anchor="lm")
    return image


def unavailable_preview(text):
    # A clearly labelled empty frame, never an invented chart.
    image = Image.new("RGB", (1000, 440), "white")
    draw = ImageDraw.Draw(image)
    font = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans")
    )
    draw.text((500, 220), text, font=ImageFont.truetype(font, 25),
              fill="#637084", anchor="mm")
    return image


def prepare_preview(figure):
    if hasattr(figure, "set_size_inches"):
        figure.set_size_inches(10, 4.4)
        figure.set_dpi(150)
        figure.set_facecolor("white")
        # Use an Image with an actual fixed height for Matplotlib previews.
        # Plot does not expose a height argument for these static figures.
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=150, facecolor="white")
        buffer.seek(0)
        with Image.open(buffer) as image:
            return image.convert("RGB").copy()
    if hasattr(figure, "update_layout"):
        figure.update_layout(
            height=PREVIEW_HEIGHT, autosize=True,
            paper_bgcolor="white", plot_bgcolor="white",
            margin={"l": 45, "r": 20, "t": 30, "b": 55},
            font={"family": "Arial, sans-serif", "color": "#17283E"}
        )
        return figure
    if isinstance(figure, Image.Image):
        return figure
    raise TypeError("Preview functions must return a Matplotlib or Plotly figure, or a PIL image.")


def find_panel(connection):
    filename = PROJECT_FOLDER / f"{connection['module']}.py"
    if not filename.exists():
        return None, "Not yet available"
    try:
        module = importlib.import_module(connection["module"])
    except Exception:
        traceback.print_exc()
        return None, "Temporarily unavailable"
    if not callable(getattr(module, connection["builder"], None)):
        print(f"Missing panel function: {connection['module']}.{connection['builder']}")
        return None, "Not yet available"
    # A missing preview should not block a working detailed analysis.
    return module, "Ready to explore"


def navigation_action(views, destination):
    def navigate():
        return [gr.update(visible=(index == destination))
                for index in range(len(views))]
    return navigate


def build_dashboard():
    connected = [find_panel(connection) for connection in PANELS]

    with gr.Blocks(
        title="Industry Performance Explorer", fill_width=True
    ) as app:
        with gr.Column(visible=True, min_width=0) as overview:
            # A single full-width banner gives the title its own background.
            gr.Image(
                value=make_title_banner(),
                label="Industry Performance Explorer",
                alt_text=(
                    "Industry Performance Explorer. Four perspectives on industry "
                    "performance. Choose an analysis to explore."
                ),
                show_label=False, container=False, interactive=False,
                buttons=[], width="100%", format="png"
            )

            explore_buttons = []
            categories = ["GROWTH", "RISK", "DIVERSIFICATION", "DISTRIBUTION"]

            for row_start in [0, 2]:
                with gr.Row(equal_height=True):
                    for index in range(row_start, row_start + 2):
                        connection = PANELS[index]
                        module, status = connected[index]

                        with gr.Column(scale=1, min_width=0):
                            with gr.Group():
                                gr.Image(
                                    value=make_card_header(
                                        connection["title"], connection["description"]
                                    ),
                                    label=connection["title"],
                                    alt_text=f"{connection['title']}. {connection['description']}",
                                    show_label=False, container=False, interactive=False,
                                    buttons=[], height=CARD_HEADER_HEIGHT,
                                    width="100%", format="png"
                                )
                                preview_fn = (
                                    getattr(module, connection["preview"], None)
                                    if module is not None else None
                                )
                                prepared = unavailable_preview("Analysis not yet connected")
                                if callable(preview_fn):
                                    try:
                                        figure = preview_fn()
                                        if figure is not None:
                                            prepared = prepare_preview(figure)
                                        else:
                                            prepared = unavailable_preview("Preview unavailable")
                                    except Exception:
                                        traceback.print_exc()
                                        prepared = unavailable_preview("Preview unavailable")
                                if isinstance(prepared, Image.Image):
                                    gr.Image(
                                        value=prepared, label=f"{connection['title']} preview",
                                        alt_text=f"Overview preview of {connection['title'].lower()}",
                                        show_label=False, container=False, interactive=False,
                                        buttons=[], height=PREVIEW_HEIGHT,
                                        width="100%", format="png"
                                    )
                                else:
                                    # Plotly respects its fixed layout height.
                                    gr.Plot(value=prepared, show_label=False, container=False)
                                # A compact right-aligned action, rather than a colour strip.
                                with gr.Row():
                                    gr.Markdown("", scale=1, min_width=0)
                                    explore_buttons.append(gr.Button(
                                        "Explore analysis →", variant="primary", size="md",
                                        scale=0, min_width=175,
                                        interactive=(module is not None)
                                    ))

        detail_views = []
        back_buttons = []
        for index, connection in enumerate(PANELS):
            module, status = connected[index]
            with gr.Column(visible=False, min_width=0) as detail_view:
                detail_views.append(detail_view)
                with gr.Row():
                    back_buttons.append(gr.Button(
                        "← All analyses", variant="secondary", size="sm",
                        scale=0, min_width=140
                    ))
                    gr.Markdown(
                        f"**0{index + 1} / {categories[index]}**",
                        min_width=0
                    )
                if module is not None:
                    try:
                        getattr(module, connection["builder"])(app)
                    except Exception:
                        traceback.print_exc()
                        gr.Markdown(
                            f"## {connection['title']}\n\n"
                            "This analysis is temporarily unavailable. "
                            "Return to the overview and choose another analysis."
                        )
                        explore_buttons[index].interactive = False
                else:
                    gr.Markdown(f"## {connection['title']}\n\n{status}")

        views = [overview] + detail_views
        for index, button in enumerate(explore_buttons, start=1):
            button.click(
                fn=navigation_action(views, index), outputs=views, queue=False
            )
        for button in back_buttons:
            button.click(
                fn=navigation_action(views, 0), outputs=views, queue=False
            )
    return app


def make_dashboard_theme():
    return gr.themes.Base(
        primary_hue="teal", secondary_hue="slate", neutral_hue="slate",
        spacing_size="sm", radius_size="sm", text_size="sm",
        font=["Arial", "sans-serif"]
    ).set(
        body_background_fill="#EFF2F6",
        body_background_fill_dark="#EFF2F6",
        background_fill_primary="#FFFFFF",
        background_fill_primary_dark="#FFFFFF",
        background_fill_secondary="#FFFFFF",
        background_fill_secondary_dark="#FFFFFF",
        block_background_fill="#FFFFFF",
        block_background_fill_dark="#FFFFFF",
        block_border_width="0px",
        block_shadow="none",
        block_padding="10px",
        layout_gap="10px",
        button_medium_padding="10px 18px",
        body_text_color="#17283E",
        body_text_color_dark="#17283E",
        body_text_color_subdued="#526174",
        body_text_color_subdued_dark="#526174",
        block_title_text_color="#17283E",
        block_title_text_color_dark="#17283E",
        block_label_text_color="#526174",
        block_label_text_color_dark="#526174",
        input_background_fill="#F5F7FA",
        input_background_fill_dark="#F5F7FA",
        input_border_color="#E3E8EF",
        input_border_color_dark="#E3E8EF"
    )


if __name__ == "__main__":
    demo = build_dashboard()
    demo.launch(inbrowser=True, theme=make_dashboard_theme())
