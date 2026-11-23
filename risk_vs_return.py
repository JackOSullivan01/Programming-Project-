from html import escape
from math import ceil, floor, isfinite
from pathlib import Path
from uuid import uuid4

import gradio as gr
import pandas as pd
import plotly.graph_objects as go


PANEL_CSS = """
.gradio-container {
    max-width: 1240px !important;
    margin-inline: auto !important;
    padding: clamp(14px, 3vw, 36px) !important;
}
.risk-panel {
    gap: 10px !important;
}
.risk-panel h1 {
    font-size: clamp(26px, 4vw, 36px);
    letter-spacing: -0.035em;
    margin: 0;
}
.risk-panel .risk-controls {
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    padding: 8px 12px;
    gap: 6px !important;
    background: var(--background-fill-primary);
}
.risk-panel .risk-controls .risk-control-row {
    gap: 8px !important;
}
.risk-panel .risk-controls label > span {
    background: transparent !important;
    color: var(--body-text-color) !important;
    padding: 0 !important;
}
.risk-panel .risk-result p {
    margin: 2px 0;
}
.risk-panel .risk-chart {
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    overflow: hidden;
    background: #30445C;
}
"""


def add_industry_labels(fig, x, y, x_range, y_range):
    # Estimate label bounds at a compact desktop chart size.
    width, height = 560, 430
    left, right = x_range
    bottom, top = y_range
    points = [
        ((risk - left) / (right - left) * width,
         (ret - bottom) / (top - bottom) * height)
        for risk, ret in zip(x, y)
    ]
    occupied = [(px - 7, py - 7, px + 7, py + 7) for px, py in points]

    for (name, risk, ret), (px, py) in zip(zip(x.index, x, y), points):
        half_width = 4 * len(name) + 4
        offsets = [
            (0, 18), (0, -18),
            (half_width + 8, 0), (-half_width - 8, 0),
            (0, 34), (0, -34),
        ]

        def placement_cost(offset):
            dx, dy = offset
            x0, x1 = px + dx - half_width, px + dx + half_width
            y0, y1 = py + dy - 8, py + dy + 8
            outside = max(0, -x0, x1 - width, -y0, y1 - height)
            overlaps = sum(
                x0 < r and x1 > l and y0 < t and y1 > b
                for l, b, r, t in occupied
            )
            return (outside > 0, overlaps, outside)

        dx, dy = min(offsets, key=placement_cost)
        occupied.append((
            px + dx - half_width, py + dy - 8,
            px + dx + half_width, py + dy + 8,
        ))
        fig.add_annotation(
            x=risk, y=ret, text=escape(name),
            showarrow=True, arrowhead=0, arrowwidth=1,
            arrowcolor="#60748A", standoff=6, ax=dx, ay=-dy,
            font=dict(size=12, color="#172B43"),
            bgcolor="rgba(239, 245, 251, 0.92)", borderpad=2,
            captureevents=False,
        )


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
        "#315E9D", "#147B78", "#AD506D", "#5C753A",
        "#AE652D", "#7556A6", "#237994", "#8B6D2B",
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

            industry_text = (
                "industry meets" if len(summary) == 1 else "industries meet"
            )
            result = (
                f"**{len(matching_industries)} of {len(summary)} "
                f"{industry_text} both targets.**"
            )
            if matching_industries:
                result += "  \n" + ", ".join(matching_industries)

            messages.append(result)

            period = frequency.lower()
            messages.append(
                f"The shaded area shows at least {target_return:g}% average "
                f"{period} return and at most {target_volatility:g}% "
                f"{period} volatility."
            )

        elif target_return is not None:
            messages.append(
                f"The dashed line marks the {target_return:g}% average "
                f"{frequency.lower()} return target. "
                + (
                    "The volatility target applies in Volatility mode."
                    if risk_measure != "Volatility"
                    else ""
                )
            )

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

        x_padding = max((x_max - x_min) * 0.23, 0.01)
        y_padding = max((y_max - y_min) * 0.23, 0.01)
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
                    line=dict(color="#FFFFFF", width=1.5),
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
                fillcolor="rgba(20, 123, 120, 0.42)",
                line_width=0,
                layer="below",
            )

        if target_return is not None:
            fig.add_hline(
                y=target_return,
                name="target-return",
                line_dash="dash",
                line_color="#AD642C",
            )

        if show_volatility_target:
            fig.add_vline(
                x=target_volatility,
                name="target-volatility",
                line_dash="dash",
                line_color="#315E9D",
            )

        add_industry_labels(fig, x, y, (left, right), (bottom, top))

        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#30445C",
            plot_bgcolor="#D6E2EE",
            font=dict(family="Inter, system-ui, sans-serif", color="#F0F5FA"),
            hoverlabel=dict(bgcolor="#172B43", font_color="#FFFFFF"),
            hovermode="closest",
            showlegend=False,
            margin=dict(l=65, r=24, t=20, b=60),
            height=510,
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
            gridcolor="#CBD7E4",
            zeroline=False,
        )

        table = (
            summary.sort_values(return_column, ascending=False)
            .rename_axis("Industry")
            .reset_index()
            .round(3)
        )
        return "\n\n".join(messages), fig, table

    def slider_settings(figure, return_target, volatility_target):
        # Keep the current targets in range when filters change.
        returns = [return_target, -2, 2]
        volatility = [volatility_target, 5]
        if figure is not None:
            returns.extend(figure.data[0].y)
            volatility.extend(figure.data[0].x)

        return (
            dict(minimum=floor(min(returns) * 1.2),
                 maximum=ceil(max(returns) * 1.2), step=0.01),
            dict(minimum=0, maximum=ceil(max(volatility) * 1.2), step=0.01),
        )

    def update_filters(
        selected, start, end, risk_measure, frequency,
        target_return, target_volatility,
    ):
        status, figure, table = update_chart(
            selected, start, end, risk_measure, frequency,
            target_return, target_volatility,
        )
        return_range, volatility_range = slider_settings(
            figure, target_return, target_volatility,
        )
        return (
            status, figure, table,
            gr.update(**return_range),
            gr.update(**volatility_range, interactive=risk_measure == "Volatility"),
        )

    initial_status, initial_plot, initial_table = update_chart(
        industries, first_date, last_date, "Volatility", default_frequency,
        default_return_target, default_volatility_target,
    )
    return_range, volatility_range = slider_settings(
        initial_plot, default_return_target, default_volatility_target,
    )
    panel_id = f"risk-return-{uuid4().hex}"

    with gr.Column(elem_classes=["risk-panel"]):
        gr.Markdown("# Risk vs Return")

        with gr.Column(elem_classes=["risk-controls"]):
            selected = gr.Dropdown(
                choices=industries,
                value=industries,
                multiselect=True,
                label="Industries",
            )
            with gr.Row(elem_classes=["risk-control-row"]):
                start = gr.DateTime(
                    label="Start date", value=first_date,
                    include_time=False, type="string",
                )
                end = gr.DateTime(
                    label="End date", value=last_date,
                    include_time=False, type="string",
                )
                frequency = gr.Dropdown(
                    choices=list(frequencies), value=default_frequency,
                    label="Frequency",
                )
                risk = gr.Dropdown(
                    choices=["Volatility", "Downside deviation"],
                    value="Volatility", label="Risk measure",
                )

            with gr.Row(elem_classes=["risk-control-row"]):
                target_return = gr.Slider(
                    **return_range, label="Minimum return (%)",
                    value=default_return_target,
                )
                target_volatility = gr.Slider(
                    **volatility_range, label="Maximum volatility (%)",
                    value=default_volatility_target,
                )

        status = gr.Markdown(initial_status, elem_classes=["risk-result"])
        plot = gr.Plot(
            value=initial_plot, show_label=False, elem_classes=["risk-chart"],
        )
        table = gr.Dataframe(
            value=initial_table, interactive=False, label="Industry statistics",
        )

        chart_inputs = [
            selected, start, end, risk, frequency,
            target_return, target_volatility,
        ]
        gr.on(
            triggers=[selected.change, start.change, end.change,
                      risk.change, frequency.change],
            fn=update_filters,
            trigger_mode="always_last",
            concurrency_id=panel_id,
            inputs=chart_inputs,
            outputs=[status, plot, table, target_return, target_volatility],
        )
        gr.on(
            triggers=[target_return.input, target_volatility.input],
            fn=update_chart,
            trigger_mode="always_last",
            concurrency_id=panel_id,
            inputs=chart_inputs,
            outputs=[status, plot, table],
        )


if __name__ == "__main__":
    csv_path = Path(__file__).with_name("industry_returns_clean.csv")
    if not csv_path.is_file():
        csv_path = csv_path.parent / "upload" / csv_path.name
    returns = pd.read_csv(csv_path)

    with gr.Blocks() as app:
        risk_vs_return_panel(returns)

    theme = gr.themes.Soft(
        primary_hue="teal", neutral_hue="slate",
        font=["Inter", "system-ui", "sans-serif"],
    )
    app.launch(server_name="0.0.0.0", theme=theme, css=PANEL_CSS)