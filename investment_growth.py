from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go


def investment_growth(monthly_returns, starting_amount, monthly_contribution):
    balances = [starting_amount]

    for monthly_return in monthly_returns:
        balance = balances[-1] * (1 + monthly_return) + monthly_contribution
        balances.append(balance)

    return balances


def build_panel(csv_path):
    daily = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date").sort_index()
    industries = daily.columns.tolist()

    # Compound daily returns into calendar-month returns.
    monthly = (1 + daily).resample("ME").prod(min_count=1) - 1
    first_month, last_month = monthly.index[[0, -1]]
    start_default = max(first_month, pd.Timestamp("2010-01-31"))
    end_default = min(last_month, pd.Timestamp("2025-12-31"))
    if start_default > end_default:
        start_default, end_default = first_month, last_month

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

        # Show the starting balance immediately before the first return.
        dates = returns.index.insert(0, returns.index[0] - pd.offsets.MonthEnd(1))
        fig = go.Figure()

        colors = [
            "#2563EB", "#0F766E", "#B45309", "#7C3AED", "#BE185D",
            "#475569", "#0369A1", "#4D7C0F", "#9F1239", "#4338CA",
        ]
        dashes = ["solid", "dash", "dot", "dashdot"]

        for index, industry in enumerate(selected):
            balances = investment_growth(returns[industry], starting_amount, contribution)
            fig.add_scatter(
                x=dates,
                y=balances,
                name=industry,
                mode="lines",
                line=dict(
                    color=colors[index % len(colors)],
                    width=2.6,
                    dash=dashes[(index // len(colors)) % len(dashes)],
                ),
                hovertemplate="$%{y:,.2f}",
            )

        fig.update_layout(
            template="plotly_white",
            height=530,
            margin=dict(l=28, r=28, t=24, b=28),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(family="Inter, Arial, sans-serif", size=13, color="#334155"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#F8FAFC", bordercolor="#CBD5E1"),
            xaxis=dict(
                hoverformat="%b %Y",
                tickformat="%b %Y" if len(returns) <= 24 else "%Y",
                nticks=7,
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
                y=-0.14,
                yanchor="top",
                title_text="",
            ),
            separators=".,",
        )
        return fig

    gr.Markdown(
        "## Investment growth\n"
        "Compare how the same starting investment and monthly contributions "
        "would have grown across industries."
    )

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=260):
            with gr.Group():
                gr.Markdown("### Investment settings")
                selected = gr.Dropdown(
                    industries,
                    value=[industry for industry in ("Technology", "Financials", "Energy")
                           if industry in industries] or industries[:3],
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
                    value=1000, minimum=0, label="Starting investment ($)"
                )
                contribution = gr.Number(
                    value=100, minimum=0, label="Monthly contribution ($)",
                    info="Added at the end of each month.",
                )

        with gr.Column(scale=3, min_width=300):
            chart = gr.Plot(
                value=draw(
                    selected.value,
                    start_year.value,
                    end_year.value,
                    starting_amount.value,
                    contribution.value,
                ),
                show_label=False,
                container=False,
            )

    # Use the existing input's click behavior when the dropdown arrow is clicked.
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

    controls = [selected, start_year, end_year, starting_amount, contribution]
    for control in controls:
        control.change(draw, inputs=controls, outputs=chart)


if __name__ == "__main__":
    with gr.Blocks() as demo:
        build_panel(Path(__file__).with_name("industry_returns_clean.csv"))

    demo.launch()
