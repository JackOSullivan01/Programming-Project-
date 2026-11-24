from pathlib import Path
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


# Standardise supplied figures without changing their underlying data.
def prepare_preview(figure):
    if hasattr(figure, "set_size_inches"):
        figure.set_size_inches(11, 5.2)
        figure.set_dpi(150)
        figure.set_facecolor("white")
    elif hasattr(figure, "update_layout"):
        figure.update_layout(
            height=340, autosize=True,
            paper_bgcolor="white", plot_bgcolor="white",
            margin={"l": 45, "r": 20, "t": 30, "b": 55},
            font={"family": "Arial, sans-serif", "color": "#17283E"}
        )
    return figure


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


def preview_loader(preview_function):
    def load_preview():
        try:
            figure = preview_function()
            if figure is None:
                return None, "Preview unavailable. Open the analysis to explore."
            return prepare_preview(figure), ""
        except Exception:
            traceback.print_exc()
            return None, "Preview unavailable. Open the analysis to explore."
    return load_preview


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
            preview_connections = []
            categories = ["GROWTH", "RISK", "DIVERSIFICATION", "DISTRIBUTION"]

            for row_start in [0, 2]:
                with gr.Row(equal_height=True):
                    for index in range(row_start, row_start + 2):
                        connection = PANELS[index]
                        module, status = connected[index]

                        with gr.Column(scale=1, min_width=0):
                            with gr.Group():
                                with gr.Row():
                                    gr.Markdown(
                                        f"**0{index + 1} / {categories[index]}**",
                                        scale=3, min_width=0
                                    )
                                    gr.Markdown(
                                        status, scale=1, min_width=0
                                    )
                                gr.Markdown(f"## {connection['title']}")
                                gr.Markdown(
                                    connection["description"], min_height=40
                                )

                                preview_fn = (
                                    getattr(module, connection["preview"], None)
                                    if module is not None else None
                                )
                                if callable(preview_fn):
                                    preview = gr.Plot(
                                        show_label=False, container=False
                                    )
                                    preview_status = gr.Markdown(min_height=25)
                                    preview_connections.append((
                                        preview_fn, preview, preview_status
                                    ))
                                else:
                                    # A blank, labelled panel rather than fabricated data.
                                    gr.Markdown(
                                        "### Your analysis will appear here\n\n"
                                        + (
                                            "The detailed analysis is ready to open."
                                            if module is not None else
                                            "This panel will become available once "
                                            "its graph file has been connected."
                                        ),
                                        min_height=340
                                    )
                                    gr.Markdown("", min_height=25)

                                explore_buttons.append(gr.Button(
                                    f"Explore {connection['title'].lower()} →",
                                    variant="primary", size="sm",
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
        for preview_function, preview, preview_status in preview_connections:
            app.load(
                fn=preview_loader(preview_function),
                outputs=[preview, preview_status],
                concurrency_id="distribution", concurrency_limit=1
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
        background_fill_secondary="#F5F7FA",
        background_fill_secondary_dark="#F5F7FA",
        block_background_fill="#FFFFFF",
        block_background_fill_dark="#FFFFFF",
        block_border_width="0px",
        block_shadow="none",
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
