from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go


PANEL_STYLE = """
<style>
#investment-growth-settings {
    background: #f8fafc;
    border: 1px solid #dbe3ec;
    border-radius: 12px;
    padding: 16px;
    gap: 10px;
    color-scheme: light;
    --background-fill-primary: #fff;
    --background-fill-secondary: #f1f5f9;
    --border-color-primary: #dbe3ec;
    --block-background-fill: transparent;
    --block-border-width: 0px;
    --block-shadow: none;
    --block-padding: 0px;
    --block-label-background-fill: transparent;
    --block-label-border-width: 0px;
    --block-label-text-color: #334155;
    --block-info-text-color: #475569;
    --body-text-color: #0f172a;
    --body-text-color-subdued: #475569;
    --input-background-fill: #fff;
    --input-background-fill-focus: #fff;
    --input-background-fill-hover: #fff;
    --input-border-color: #cbd5e1;
    --input-border-color-focus: #0f766e;
    --input-placeholder-color: #64748b;
    --input-shadow-focus: 0 0 0 2px #99f6e4;
}
#investment-growth-settings h3 {
    margin: 0 0 4px;
    color: #0f172a;
    font-size: 1rem;
    background: transparent;
}
#investment-growth-settings label > span { color: #334155; }
#investment-growth-settings input {
    color: #0f172a;
    caret-color: #0f172a;
    accent-color: #0f766e;
}
#investment-growth-summary {
    padding: 12px 16px;
    border: 1px solid #dbe3ec;
    border-left: 3px solid #0f766e;
    border-radius: 10px;
    background: #f8fafc;
}
#investment-growth-summary strong { color: #0f172a; }
#investment-growth-summary p { margin: 0; color: #475569; }
#investment-growth-summary p + p { margin-top: 4px; }
#investment-growth-chart {
    overflow: hidden;
    border: 1px solid #dbe3ec;
    border-radius: 12px;
    background: #fff;
}
</style>
"""

LINE_COLORS = (
    "#2563A6", "#0F766E", "#A45D24", "#71558C", "#A34162",
    "#475569", "#087D9A", "#517037", "#8D4242", "#4D5591",
)
LINE_DASHES = ("solid", "dash", "dot", "dashdot")


def investment_growth(monthly_returns, starting_amount, monthly_contribution):
    balances = [starting_amount]

    for monthly_return in monthly_returns:
        balance = balances[-1] * (1 + monthly_return) + monthly_contribution
        balances.append(balance)

    return balances


def build_panel(csv_path):
    daily = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date").sort_index()
    industries = daily.columns.tolist()
    industry_order = {industry: index for index, industry in enumerate(industries)}

    # Compound daily returns into calendar-month returns.
    monthly = (1 + daily).resample("ME").prod(min_count=1) - 1
    first_month, last_month = monthly.index[[0, -1]]
    start_default = max(first_month, pd.Timestamp("2010-01-31"))
    end_default = min(last_month, pd.Timestamp("2025-12-31"))
    if start_default > end_default:
        start_default, end_default = first_month, last_month

    default_industries = [
        industry for industry in ("Technology", "Financials", "Energy")
        if industry in industry_order
    ] or industries[:3]

    def draw(selected, start_year, end_year, starting_amount, contribution):
        if not selected:
            raise gr.Error("Choose at least one industry.")
        if None in (start_year, end_year, starting_amount, contribution):
            raise gr.Error("Enter both years and both dollar amounts.")
        if start_year > end_year:
            raise gr.Error("Start year must be at or before end year.")
        if starting_amount < 0 or contribution < 0:
            raise gr.Error("Dollar amounts must be zero or greater.")

        returns = monthly.loc[str(int(start_year)):str(int(end_year)), selected]
        if returns.empty or returns.isna().any().any():
            raise gr.Error("Choose a range with monthly returns for every selected industry.")

        # Include the starting balance before applying the first month's return.
        dates = returns.index.insert(0, returns.index[0] - pd.offsets.MonthEnd(1))
        fig = go.Figure()
        ending_values = []

        for industry in selected:
            balances = investment_growth(returns[industry], starting_amount, contribution)
            ending_values.append(balances[-1])
            index = industry_order[industry]
            color = LINE_COLORS[index % len(LINE_COLORS)]
            dash = LINE_DASHES[(index // len(LINE_COLORS)) % len(LINE_DASHES)]
            fig.add_scatter(
                x=dates,
                y=balances,
                name=industry,
                mode="lines+markers",
                line=dict(color=color, width=2.4, dash=dash),
                marker=dict(color=color, size=[0] * len(returns) + [7]),
                hovertemplate="$%{y:,.2f}",
            )

        fig.update_layout(
            template="plotly_white",
            height=500,
            margin=dict(l=72, r=22, t=20, b=66),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(family="Inter, Arial, sans-serif", size=13, color="#334155"),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#FFFFFF",
                bordercolor="#CBD5E1",
                font=dict(color="#0F172A"),
            ),
            xaxis=dict(
                hoverformat="%b %Y",
                tickformat="%b %Y" if len(returns) <= 24 else "%Y",
                nticks=6,
                ticks="outside",
                ticklen=4,
                tickcolor="#CBD5E1",
                showgrid=False,
                showline=True,
                linecolor="#CBD5E1",
                automargin=True,
            ),
            yaxis=dict(
                title="Portfolio value",
                tickprefix="$",
                tickformat=",.0f",
                gridcolor="#E2E8F0",
                zeroline=False,
                automargin=True,
            ),
            legend=dict(
                orientation="h",
                x=0,
                y=-0.13,
                yanchor="top",
                bgcolor="rgba(0,0,0,0)",
                title_text="",
            ),
            separators=".,",
        )

        lowest, highest = min(ending_values), max(ending_values)
        ending_value = f"${lowest:,.2f}"
        if f"{lowest:.2f}" != f"{highest:.2f}":
            ending_value += f"–${highest:,.2f}"
        total_invested = starting_amount + contribution * len(returns)
        summary = (
            f"**Ending portfolio value · {ending_value}**\n\n"
            f"${total_invested:,.2f} invested per industry · "
            f"{returns.index[0]:%b %Y} to {returns.index[-1]:%b %Y}\n"
        )
        return summary, fig

    gr.HTML(PANEL_STYLE, container=False)
    gr.Markdown(
        "## Investment growth\n"
        "Compare how the same investment would have grown across industries."
    )

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=250, elem_id="investment-growth-settings"):
            gr.Markdown("### Investment settings")
            selected = gr.Dropdown(
                choices=industries,
                value=default_industries,
                multiselect=True,
                label="Industries",
                elem_id="investment-growth-industries",
            )
            with gr.Row():
                start_year = gr.Number(
                    value=start_default.year,
                    minimum=first_month.year,
                    maximum=last_month.year,
                    precision=0,
                    label="Start year",
                    min_width=90,
                )
                end_year = gr.Number(
                    value=end_default.year,
                    minimum=first_month.year,
                    maximum=last_month.year,
                    precision=0,
                    label="End year",
                    min_width=90,
                )
            starting_amount = gr.Number(
                value=1000,
                minimum=0,
                step=100,
                label="Starting investment ($)",
            )
            contribution = gr.Number(
                value=100,
                minimum=0,
                step=25,
                label="Monthly contribution ($)",
                info="Added at the end of each month.",
            )

        controls = [selected, start_year, end_year, starting_amount, contribution]
        initial_summary, initial_figure = draw(*(control.value for control in controls))
        with gr.Column(scale=4, min_width=300):
            summary = gr.Markdown(initial_summary, elem_id="investment-growth-summary")
            chart = gr.Plot(
                value=initial_figure,
                show_label=False,
                container=False,
                elem_id="investment-growth-chart",
            )

    # Forward clicks on the dropdown arrow to the underlying input.
    gr.on(
        fn=None,
        js="""() => {
            const id = "investment-growth-industries";
            const dropdown = document.getElementById(id)
                ?? document.querySelector("gradio-app")?.shadowRoot?.getElementById(id);
            if (!dropdown || dropdown.dataset.arrowClickBound) return;
            dropdown.dataset.arrowClickBound = "true";

            const arrowSelector = ".dropdown-arrow, .dropdown-arrow-wrap";
            for (const arrow of dropdown.querySelectorAll(arrowSelector)) {
                arrow.style.pointerEvents = "auto";
                arrow.style.cursor = "pointer";
            }

            dropdown.addEventListener("click", (event) => {
                if (!event.target.closest(arrowSelector)) return;
                const input = dropdown.querySelector("input");
                if (!input || input.disabled) return;
                event.preventDefault();
                event.stopPropagation();
                input.focus();
                input.click();
            }, true);
        }""",
    )

    gr.on(
        triggers=[control.change for control in controls],
        fn=draw,
        inputs=controls,
        outputs=[summary, chart],
    )


if __name__ == "__main__":
    with gr.Blocks() as demo:
        build_panel(Path(__file__).with_name("industry_returns_clean.csv"))

    demo.launch()
