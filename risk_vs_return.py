from math import isfinite
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go


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

        start_date = pd.to_datetime(start, errors="coerce")
        end_date = pd.to_datetime(end, errors="coerce")
        if pd.isna(start_date) or pd.isna(end_date):
            return "Choose both a start date and an end date.", None, empty_table

        start_date = start_date.normalize()
        end_date = end_date.normalize()
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

        period_returns = returns.loc[start_date:end_date, selected]

        # Compound daily returns within each selected week, month, or year.
        rule = frequencies[frequency]
        if rule is not None:
            period_returns = (
                (1 + period_returns).resample(rule).prod(min_count=1) - 1
            )

        if risk_measure == "Volatility":
            risk = period_returns.std()
        else:
            # Returns below zero contribute to downside deviation.
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
        show_target_region = target_return is not None and show_volatility_target

        if show_target_region:
            meets_both = (
                (summary[return_column] >= target_return)
                & (summary[risk_column] <= target_volatility)
            )
            matching_industries = (
                summary.loc[meets_both]
                .sort_values(return_column, ascending=False)
                .index.tolist()
            )
            messages.append(
                f"**{len(matching_industries)} of {len(summary)} plotted "
                "industries meet both targets.**"
            )
            if matching_industries:
                messages.append(", ".join(matching_industries))

        omitted = len(selected) - len(summary)
        if omitted:
            messages.append(
                f"Industries omitted due to insufficient data: **{omitted}**."
            )

        x = summary[risk_column]
        y = summary[return_column]

        # Include both the plotted points and any active target lines.
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()

        if show_volatility_target:
            x_min = min(x_min, target_volatility)
            x_max = max(x_max, target_volatility)

        if target_return is not None:
            y_min = min(y_min, target_return)
            y_max = max(y_max, target_return)

        x_padding = max((x_max - x_min) * 0.15, 0.01)
        y_padding = max((y_max - y_min) * 0.15, 0.01)
        left = max(0, x_min - x_padding)
        right = x_max + x_padding
        bottom = y_min - y_padding
        top = y_max + y_padding

        fig = go.Figure(
            go.Scatter(
                x=x.tolist(),
                y=y.tolist(),
                mode="markers",
                text=summary.index.tolist(),
                marker=dict(
                    size=11,
                    color=[colors[name] for name in summary.index],
                    line=dict(color="#242527", width=1),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    + risk_label + ": %{x:.4f}%<br>"
                    + return_label + ": %{y:.4f}%"
                    + "<extra></extra>"
                ),
            )
        )

        if show_target_region:
            fig.add_shape(
                type="rect",
                xref="x",
                yref="y",
                x0=0,
                x1=target_volatility,
                y0=target_return,
                y1=top,
                fillcolor="rgba(209, 213, 219, 0.16)",
                line_width=0,
                layer="below",
            )

        if target_return is not None:
            fig.add_hline(
                y=target_return,
                line_dash="dash",
                line_color="#F1B96A",
                annotation_text=f"Target return {target_return:g}%",
                annotation_position="top right",
            )

        if show_volatility_target:
            fig.add_vline(
                x=target_volatility,
                line_dash="dash",
                line_color="#83A9FF",
                annotation_text=f"Target volatility {target_volatility:g}%",
                annotation_position="top right",
            )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#242527",
            plot_bgcolor="#242527",
            hovermode="closest",
            showlegend=False,
            margin=dict(l=65, r=45, t=45, b=55),
            height=480,
        )
        fig.update_xaxes(
            title_text=risk_label,
            range=[left, right],
            ticksuffix="%",
            showgrid=False,
            zeroline=False,
        )
        fig.update_yaxes(
            title_text=return_label,
            range=[bottom, top],
            ticksuffix="%",
            gridcolor="#45474D",
            zeroline=False,
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
            start = gr.DateTime(
                label="Start date",
                value=first_date,
                include_time=False,
                type="string",
            )
            end = gr.DateTime(
                label="End date",
                value=last_date,
                include_time=False,
                type="string",
            )
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
                label="Target return (%)",
                value=default_return_target,
            )
            target_volatility = gr.Number(
                label="Target volatility (%)",
                value=default_volatility_target,
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

    app.launch(server_name="0.0.0.0")