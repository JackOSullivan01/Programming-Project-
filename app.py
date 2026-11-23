from pathlib import Path

import gradio as gr
import pandas as pd

from investment_growth import build_panel as investment_growth_panel
from risk_vs_return import PANEL_CSS, risk_vs_return_panel
from correlation_heatmap import build_panel as correlation_heatmap_panel
from return_distribution import build_panel as return_distribution_panel


DATA_FILE = Path(__file__).with_name("industry_returns_clean.csv")


def build_dashboard():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"Place {DATA_FILE.name} beside app.py.")

    # Keep Date as a column for the risk-versus-return panel.
    daily_returns = pd.read_csv(DATA_FILE, parse_dates=["Date"])

    with gr.Blocks(title="Industry Performance Explorer") as dashboard:
        gr.Markdown("# Industry Performance Explorer")
        gr.Markdown(
            "Compare historical industry returns, volatility, "
            "and how industries move together."
        )

        with gr.Tabs():
            with gr.Tab("Investment Growth"):
                investment_growth_panel(DATA_FILE)

            with gr.Tab("Risk vs Return"):
                risk_vs_return_panel(daily_returns)

            with gr.Tab("Correlation Heatmap"):
                correlation_heatmap_panel(DATA_FILE)

            with gr.Tab("Return Distribution"):
                return_distribution_panel(DATA_FILE)

    return dashboard


if __name__ == "__main__":
    dashboard = build_dashboard()
    theme = gr.themes.Soft(primary_hue="teal", neutral_hue="slate")
    dashboard.launch(server_name="0.0.0.0", theme=theme, css=PANEL_CSS)