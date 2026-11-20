from math import isfinite
from pathlib import Path

import gradio as gr
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter


def risk_vs_return_panel(returns):
    returns = returns.copy()
    returns["Date"] = pd.to_datetime(returns["Date"])
    returns = returns.sort_values("Date").set_index("Date")

    industries = returns.columns.tolist()
    first_date = returns.index.min().strftime("%Y-%m-%d")
    last_date = returns.index.max().strftime("%Y-%m-%d")

    frequencies = {
        "Daily": None,
        "Weekly": "W-FRI",
        "Monthly": "ME",
        "Annual": "YE",
    }
    palette = [
        "#4268B0", "#42897E", "#C46E70", "#668A54",
        "#B9774D", "#7967A8", "#4188A4", "#9B715B",
    ]
    colors = {
        name: palette[i % len(palette)]
        for i, name in enumerate(industries)
    }

    def update_chart(
        selected, start, end, risk_measure, frequency,
        target_return, target_volatility,
    ):
        if not selected:
            raise gr.Error("Choose at least one industry.")

        start_date = pd.to_datetime(
            start, format="%Y-%m-%d", errors="coerce"
        )
        end_date = pd.to_datetime(
            end, format="%Y-%m-%d", errors="coerce"
        )
        if pd.isna(start_date) or pd.isna(end_date):
            raise gr.Error("Enter both dates in YYYY-MM-DD format.")
        if start_date > end_date:
            raise gr.Error("The start date must come before or equal the end date.")

        if target_return is not None and not isfinite(target_return):
            raise gr.Error("Enter a finite return target.")
        if target_volatility is not None and (
            not isfinite(target_volatility) or target_volatility < 0
        ):
            raise gr.Error("Enter a volatility target of zero or greater.")

        # Filter first so the chart only uses the dates requested.
        period_returns = returns.loc[start_date:end_date, selected]

        # Compound daily returns into the chosen periods.
        rule = frequencies[frequency]
        if rule is not None:
            period_returns = (
                (1 + period_returns).resample(rule).prod(min_count=1) - 1
            )

        return_label = f"Average {frequency.lower()} return"
        volatility_label = f"{frequency} volatility"

        if risk_measure == "Volatility":
            risk = period_returns.std()
            risk_label = volatility_label
        else:
            # Returns below zero contribute to downside deviation.
            risk = period_returns.clip(upper=0).pow(2).mean() ** 0.5
            risk_label = f"{frequency} downside deviation"

        summary = pd.DataFrame({
            f"{risk_label} (%)": risk * 100,
            f"{return_label} (%)": period_returns.mean() * 100,
        })
        summary = summary.loc[period_returns.count() >= 2].dropna()

        if summary.empty:
            raise gr.Error(
                f"Choose a date range with at least two {frequency.lower()} observations."
            )

        fig = Figure(figsize=(9, 4.2), layout="constrained")
        ax = fig.subplots()
        ax.set_axisbelow(True)
        ax.grid(color="#E4E9EF", linewidth=0.8)

        for name, (risk_pct, return_pct) in summary.iterrows():
            ax.scatter(risk_pct, return_pct, color=colors[name], s=55, zorder=3)
            ax.annotate(
                name,
                (risk_pct, return_pct),
                xytext=(7, 5),
                textcoords="offset points",
                fontsize=9,
                color="#263445",
            )

        if target_return is not None:
            ax.axhline(
                target_return,
                color="#B87830",
                linestyle="--",
                label=f"Target return {target_return:g}%",
            )

        if target_volatility is not None and risk_measure == "Volatility":
            ax.axvline(
                target_volatility,
                color="#4268B0",
                linestyle="--",
                label=f"Target volatility {target_volatility:g}%",
            )

        if ax.lines:
            ax.legend(loc="best")

        ax.set_xlabel(risk_label)
        ax.set_ylabel(return_label)
        ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.margins(x=0.23, y=0.17)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        table = summary.rename_axis("Industry").reset_index().round(3)
        return fig, table

    with gr.Group():
        gr.Markdown("## Risk vs Return")

        selected = gr.Dropdown(
            choices=industries,
            value=industries,
            multiselect=True,
            label="Industries",
        )

        with gr.Row():
            start = gr.Textbox(label="Start date (YYYY-MM-DD)", value=first_date)
            end = gr.Textbox(label="End date (YYYY-MM-DD)", value=last_date)

        with gr.Row():
            risk = gr.Dropdown(
                choices=["Volatility", "Downside deviation"],
                value="Volatility",
                label="Risk measure",
            )
            frequency = gr.Dropdown(
                choices=list(frequencies),
                value="Monthly",
                label="Frequency",
            )

        with gr.Row():
            target_return = gr.Number(label="Target return (%)", value=1)
            target_volatility = gr.Number(label="Target volatility (%)", value=5)

        gr.Markdown(
            "Targets use the selected frequency. "
            "The volatility target appears when Volatility is selected."
        )

        update = gr.Button("Update chart")
        initial_plot, initial_table = update_chart(
            industries, first_date, last_date, "Volatility", "Monthly", 1, 5
        )
        plot = gr.Plot(value=initial_plot, show_label=False)
        table = gr.Dataframe(
            value=initial_table, interactive=False, label="Industry statistics"
        )

        update.click(
            update_chart,
            inputs=[
                selected, start, end, risk, frequency,
                target_return, target_volatility,
            ],
            outputs=[plot, table],
        )


if __name__ == "__main__":
    csv_path = Path(__file__).with_name("industry_returns_clean.csv")
    returns = pd.read_csv(csv_path)

    with gr.Blocks() as app:
        risk_vs_return_panel(returns)

    app.launch(server_name="0.0.0.0", server_port=7860)