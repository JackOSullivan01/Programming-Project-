from math import isfinite
from pathlib import Path

import gradio as gr
import pandas as pd
from adjustText import adjust_text
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, PercentFormatter


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
        "#8EAEFF", "#73D6BD", "#F6A6B2", "#B0D783",
        "#F0B485", "#C3A5FF", "#83CFEC", "#E3D18B",
    ]
    colors = {
        name: palette[i % len(palette)]
        for i, name in enumerate(industries)
    }

    default_frequency = "Monthly"
    default_return_target = 1
    default_volatility_target = 5

    def update_chart(
        selected, start, end, risk_measure, frequency,
        target_return, target_volatility,
    ):
        risk_label = f"{frequency} {risk_measure.lower()}"
        return_label = f"Average {frequency.lower()} return"
        risk_column = f"{risk_label} (%)"
        return_column = f"{return_label} (%)"
        empty_table = pd.DataFrame(
            columns=["Industry", risk_column, return_column]
        )

        if not selected:
            return "Choose at least one industry.", None, empty_table

        start_date = pd.to_datetime(
            start, format="%Y-%m-%d", errors="coerce"
        )
        end_date = pd.to_datetime(
            end, format="%Y-%m-%d", errors="coerce"
        )
        if pd.isna(start_date) or pd.isna(end_date):
            return "Enter both dates in `YYYY-MM-DD` format.", None, empty_table

        if start_date > end_date:
            return "The end date must be on or after the start date.", None, empty_table

        show_volatility_target = (
            risk_measure == "Volatility" and target_volatility is not None
        )

        if target_return is not None and not isfinite(target_return):
            return "Enter a finite return target.", None, empty_table

        if show_volatility_target and (
            not isfinite(target_volatility) or target_volatility < 0
        ):
            return "Enter a volatility target of zero or greater.", None, empty_table

        # Filter to the selected dates and industries.
        period_returns = returns.loc[start_date:end_date, selected]

        # Compound daily returns within each week, month, or year.
        rule = frequencies[frequency]
        if rule is not None:
            period_returns = (
                (1 + period_returns).resample(rule).prod(min_count=1) - 1
            )

        if risk_measure == "Volatility":
            risk = period_returns.std()
        else:
            # Only returns below zero contribute to downside deviation.
            risk = period_returns.clip(upper=0).pow(2).mean() ** 0.5

        summary = pd.DataFrame({
            risk_column: risk * 100,
            return_column: period_returns.mean() * 100,
        })
        summary = summary.loc[period_returns.count() >= 2].dropna()

        if summary.empty:
            return (
                f"Choose a date range with at least two usable "
                f"{frequency.lower()} observations.",
                None,
                empty_table,
            )

        messages = []

        if target_return is not None and show_volatility_target:
            meets_both = (
                (summary[return_column] >= target_return)
                & (summary[risk_column] <= target_volatility)
            )
            messages.append(
                f"**{meets_both.sum()} of {len(summary)} plotted industries "
                f"meet both targets.**"
            )

        omitted = len(selected) - len(summary)
        if omitted:
            messages.append(
                f"Industries omitted due to insufficient data: **{omitted}**."
            )

        background = "#242527"
        foreground = "#E8EAF0"
        fig = Figure(
            figsize=(10, 4.8), facecolor=background, layout="constrained"
        )
        ax = fig.subplots()
        ax.set_facecolor(background)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#484B53", linewidth=0.7, alpha=0.65)

        x = summary[risk_column]
        y = summary[return_column]
        dots = ax.scatter(
            x,
            y,
            c=[colors[name] for name in summary.index],
            s=64,
            edgecolors=background,
            linewidths=0.8,
            zorder=3,
        )

        if target_return is not None:
            ax.axhline(
                target_return,
                color="#F1B96A",
                linestyle="--",
                linewidth=1.2,
                label=f"Target return {target_return:g}%",
            )

        if show_volatility_target:
            ax.axvline(
                target_volatility,
                color="#83A9FF",
                linestyle="--",
                linewidth=1.2,
                label=f"Target volatility {target_volatility:g}%",
            )

        if ax.lines:
            ax.legend(
                loc="lower left",
                bbox_to_anchor=(0, 1.02),
                ncol=2,
                frameon=False,
                labelcolor=foreground,
                fontsize=9,
            )

        ax.set_xlabel(risk_label, color=foreground, labelpad=8)
        ax.set_ylabel(return_label, color=foreground, labelpad=8)
        ax.tick_params(axis="both", colors="#C9CDD5", labelsize=9, length=0)

        ax.xaxis.set_major_locator(MaxNLocator(nbins=7))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

        for edge in ("top", "right", "left"):
            ax.spines[edge].set_visible(False)
        ax.spines["bottom"].set_color("#666A73")
        ax.margins(x=0.23, y=0.17)

        if len(summary) == 1:
            ax.annotate(
                summary.index[0],
                (x.iloc[0], y.iloc[0]),
                xytext=(9, 6),
                textcoords="offset points",
                fontsize=9,
                color=foreground,
            )
        else:
            labels = [
                ax.text(risk_pct, return_pct, name, fontsize=9, color=foreground)
                for name, (risk_pct, return_pct) in summary.iterrows()
            ]
            adjust_text(
                labels,
                objects=dots,
                ax=ax,
                expand=(1.15, 1.30),
                arrowprops=dict(arrowstyle="-", color="#9FA6B2", lw=0.7),
            )

        table = (
            summary.sort_values(return_column, ascending=False)
            .rename_axis("Industry")
            .reset_index()
            .round(3)
        )
        return "\n\n".join(messages), fig, table

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
            frequency = gr.Dropdown(
                choices=list(frequencies),
                value=default_frequency,
                label="Frequency",
            )

        with gr.Row():
            risk = gr.Dropdown(
                choices=["Volatility", "Downside deviation"],
                value="Volatility",
                label="Risk measure",
            )
            target_return = gr.Number(
                label="Target return (%)", value=default_return_target
            )
            target_volatility = gr.Number(
                label="Target volatility (%)", value=default_volatility_target
            )

        with gr.Row():
            gr.Markdown(
                "Targets use the selected frequency. "
                "The volatility target applies in Volatility mode."
            )
            update = gr.Button("Update chart", variant="primary")

        initial_status, initial_plot, initial_table = update_chart(
            industries,
            first_date,
            last_date,
            "Volatility",
            default_frequency,
            default_return_target,
            default_volatility_target,
        )

        status = gr.Markdown(initial_status)
        plot = gr.Plot(value=initial_plot, show_label=False)
        table = gr.Dataframe(
            value=initial_table,
            interactive=False,
            label="Industry statistics",
        )

        update.click(
            update_chart,
            inputs=[
                selected, start, end, risk, frequency,
                target_return, target_volatility,
            ],
            outputs=[status, plot, table],
        )


if __name__ == "__main__":
    csv_path = Path(__file__).with_name("industry_returns_clean.csv")
    returns = pd.read_csv(csv_path)

    with gr.Blocks() as app:
        risk_vs_return_panel(returns)

    app.launch(server_name="0.0.0.0", server_port=7861)