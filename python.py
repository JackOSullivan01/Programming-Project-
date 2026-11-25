from pathlib import Path
from io import BytesIO
import base64
import importlib
import traceback

import pandas as pd
import gradio as gr
import plotly.graph_objects as go
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
        "module": "risk_vs_return",
        "preview": "make_risk_preview",
        "builder": "risk_vs_return_panel"
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
    # A slim, centred title with no secondary sentence or decorative underline.
    width, height = 2200, 115
    image = Image.new("RGB", (width, height), "#17283E")
    draw = ImageDraw.Draw(image)
    bold_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    draw.text(
        (width / 2, height / 2), "Industry Performance Explorer",
        font=ImageFont.truetype(bold_path, 54),
        fill="#FFFFFF", anchor="mm"
    )
    return image


PREVIEW_HEIGHT = 210


def make_card_header(title, description):
    # Quiet, identical white title strips keep attention on the charts.
    width, height = 1200, 68
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    bold = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    draw.text((26, height / 2), title,
              font=ImageFont.truetype(bold, 34),
              fill="#17283E", anchor="lm")
    return image


def unavailable_preview(text):
    # A clearly labelled empty frame, never an invented chart.
    image = Image.new("RGB", (1000, 350), "white")
    draw = ImageDraw.Draw(image)
    font = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans")
    )
    draw.text((500, 175), text, font=ImageFont.truetype(font, 25),
              fill="#637084", anchor="mm")
    return image


def white_preview_frame(image):
    # Fill the entire preview frame with white, including aspect-ratio margins.
    # The image remains proportional; the chart itself is never stretched.
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    source = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    figure = go.Figure(go.Image(source=source, hoverinfo="skip"))
    figure.update_layout(
        height=PREVIEW_HEIGHT, autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        template="plotly_white", showlegend=False,
        dragmode=False, hovermode=False,
        modebar_remove=["zoom2d", "pan2d", "select2d", "lasso2d",
                        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]
    )
    figure.update_xaxes(visible=False, fixedrange=True, constrain="domain")
    figure.update_yaxes(visible=False, fixedrange=True, scaleanchor="x",
                         scaleratio=1, constrain="domain", autorange="reversed")
    return figure


def prepare_preview(figure):
    if hasattr(figure, "set_size_inches"):
        figure.set_size_inches(10, 4)
        figure.set_dpi(150)
        figure.set_facecolor("white")
        # Use an Image with an actual fixed height for Matplotlib previews.
        # Plot does not expose a height argument for these static figures.
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=150, facecolor="white")
        buffer.seek(0)
        with Image.open(buffer) as image:
            return white_preview_frame(image.convert("RGB").copy())
    if hasattr(figure, "update_layout"):
        figure.update_layout(
            height=PREVIEW_HEIGHT, autosize=True,
            paper_bgcolor="white", plot_bgcolor="white",
            margin={"l": 45, "r": 20, "t": 30, "b": 55},
            font={"family": "Arial, sans-serif", "color": "#17283E"}
        )
        return figure
    if isinstance(figure, Image.Image):
        return white_preview_frame(figure)
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
                                    buttons=[],
                                    width="100%", format="png"
                                )
                                preview_fn = (
                                    getattr(module, connection["preview"], None)
                                    if module is not None else None
                                )

                                # Generate the preview using his existing graph function
                                

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
                                    prepared = white_preview_frame(prepared)
                                # Plotly's white paper fills the complete fixed-height frame.
                                gr.Plot(value=prepared, show_label=False, container=False)
                                # A compact right-aligned action, rather than a colour strip.
                                with gr.Row():
                                    gr.Markdown("", scale=1, min_width=0)
                                    explore_buttons.append(gr.Button(
                                        "Explore analysis →", variant="secondary", size="sm",
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
                        build_panel = getattr(module, connection["builder"])

                        if connection["builder"] == "build_correlation_panel":
                            # Connect the existing correlation panel
                            _, panel_inputs, panel_outputs = build_panel()

                            app.load(
                                fn=module.update_correlation_panel,
                                inputs=panel_inputs,
                                outputs=panel_outputs
                            )

                        elif connection["builder"] == "risk_vs_return_panel":
                            # His risk panel expects a table with a Date column
                            returns = pd.read_csv(
                                PROJECT_FOLDER / "industry_returns_clean.csv"
                            )

                            build_panel(returns)

                        else:
                            build_panel(app)
                        
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
        panel_background_fill="#FFFFFF",
        panel_background_fill_dark="#FFFFFF",
        panel_border_width="1px",
        panel_border_width_dark="1px",
        panel_border_color="#E4E9F0",
        panel_border_color_dark="#E4E9F0",
        button_secondary_background_fill="#F5F7FA",
        button_secondary_background_fill_dark="#F5F7FA",
        button_secondary_text_color="#334155",
        button_secondary_text_color_dark="#334155",
        button_secondary_border_color="#DCE3EC",
        button_secondary_border_color_dark="#DCE3EC",
        button_secondary_background_fill_hover="#E8F3F2",
        button_secondary_background_fill_hover_dark="#E8F3F2",
        button_secondary_text_color_hover="#087F83",
        button_secondary_text_color_hover_dark="#087F83",
        block_background_fill="#FFFFFF",
        block_label_background_fill="#FFFFFF",
        block_label_background_fill_dark="#FFFFFF",
        block_background_fill_dark="#FFFFFF",
        block_border_width="0px",
        block_shadow="none",
        block_padding="6px",
        layout_gap="12px",
        button_medium_padding="8px 16px",
        button_small_padding="8px 16px",
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

