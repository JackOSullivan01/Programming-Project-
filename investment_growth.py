from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go


def investment_growth(monthly_returns, starting_amount, monthly_contribution):
    balances = [starting_amount]

    # work out the balence each month
    for monthly_return in monthly_returns:
        balance = balances[-1] * (1 + monthly_return) + monthly_contribution
        balances.append(balance)

    return balances


def build_panel(csv_path):
    daily = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date").sort_index()
    industries = daily.columns.tolist()

    # put the daily numbers togther by month
    monthly = (1 + daily).resample("ME").prod(min_count=1) - 1
    first_month, last_month = monthly.index[[0, -1]]
    start_default = max(first_month, pd.Timestamp("2010-01-31"))
    end_default = min(last_month, pd.Timestamp("2025-12-31"))

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

        # add the first point seperate from the rest
        dates = returns.index.insert(0, returns.index[0] - pd.offsets.MonthEnd(1))
        fig = go.Figure()

        for industry in selected:
            balances = investment_growth(returns[industry], starting_amount, contribution)
            fig.add_scatter(
                x=dates,
                y=balances,
                name=industry,
                mode="lines",
                hovertemplate="%{x|%b %Y}<br>$%{y:,.2f}",
            )

        fig.update_layout(
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Investment value",
            yaxis_tickprefix="$",
            yaxis_tickformat=",.0f",
            legend=dict(orientation="h", y=-0.22),
            hovermode="x unified",
        )
        return fig

    gr.Markdown("## Investment growth")

    with gr.Row():
        selected = gr.Dropdown(
            industries,
            value=["Technology", "Financials", "Energy"],
            multiselect=True,
            label="Industries",
        )
        start_year = gr.Number(
            value=start_default.year,
            minimum=first_month.year,
            maximum=last_month.year,
            precision=0,
            label="Start year",
        )
        end_year = gr.Number(
            value=end_default.year,
            minimum=first_month.year,
            maximum=last_month.year,
            precision=0,
            label="End year",
        )

    with gr.Row():
        starting_amount = gr.Number(value=1000, minimum=0, label="Starting investment ($)")
        contribution = gr.Number(value=100, minimum=0, label="Monthly contribution ($)")

    chart = gr.Plot(
        value=draw(
            selected.value,
            start_year.value,
            end_year.value,
            starting_amount.value,
            contribution.value,
        ),
        show_label=False,
    )

    controls = [selected, start_year, end_year, starting_amount, contribution]
    for control in controls:
        control.change(draw, inputs=controls, outputs=chart)


if __name__ == "__main__":
    with gr.Blocks() as demo:
        build_panel(Path(__file__).with_name("industry_returns_clean.csv"))

    demo.launch()