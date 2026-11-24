from pathlib import Path

import gradio as gr
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots
from scipy import stats


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

filename = Path(__file__).parent / "industry_returns_clean.csv"

df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
).sort_index()

SECTORS = list(df.columns)

DEFAULT_SECTORS = [
    sector
    for sector in [
        "Technology",
        "Financials",
        "Healthcare",
        "Energy"
    ]
    if sector in SECTORS
]

if not DEFAULT_SECTORS:
    DEFAULT_SECTORS = SECTORS[:4]

FIRST_DATE = df.index.min().strftime("%Y-%m-%d")
LAST_DATE = df.index.max().strftime("%Y-%m-%d")

NAVY = "#17283E"
RED = "#B84A42"

PALETTE = {
    "Technology": "#245A91",
    "Financials": "#B17822",
    "Healthcare": "#087F83",
    "Energy": "#B84A42",
    "Consumer goods": "#79538F",
    "Industrials": "#3A7A54",
    "Utilities": "#8D653F",
    "Real estate": "#445365"
}

PANELS = [
    "Investment growth",
    "Risk versus return",
    "Industry correlations",
    "Return distributions"
]

CHART_TYPES = [
    "Histogram",
    "Box plot",
    "Violin plot",
    "Cumulative probability",
    "Normal Q-Q"
]


# --------------------------------------------------
# DESCRIPTIONS AND EXPLANATIONS
# --------------------------------------------------

PREVIEW_DESCRIPTIONS = {
    "Investment growth":
        "The historical path of a $1,000 investment.",
    "Risk versus return":
        "Annualised growth compared with return volatility.",
    "Industry correlations":
        "How closely sector returns moved together.",
    "Return distributions":
        "The shape and spread of monthly sector returns."
}

DESCRIPTIONS = {
    "Investment growth":
        "Compare how a hypothetical investment would have grown "
        "across sectors through reinvested historical returns.",

    "Risk versus return":
        "Compare compound annual growth with volatility. Further right "
        "means greater fluctuations; higher means stronger historical growth.",

    "Industry correlations":
        "Explore which sectors moved together during the selected period.",

    "Return distributions":
        "Compare typical returns, their spread and extreme historical outcomes."
}

READING_GUIDES = {
    "Investment growth":
        "Each line follows the value of the same starting investment "
        "in a different sector. Hover over a date to compare values.",

    "Risk versus return":
        "Each point represents a sector. The horizontal axis measures "
        "annualised volatility; the vertical axis measures compound "
        "annual growth. Higher returns and lower volatility occupy "
        "the upper-left part of the chart.",

    "Industry correlations":
        "Values near +1 indicate similar movements, values near zero "
        "indicate weak linear relationships, and values near −1 "
        "indicate opposite movements."
}

METHODS = {
    "Investment growth":
        "Investment value = starting amount × cumulative product of "
        "(1 + return). Assumes reinvestment and excludes fees, taxes "
        "and additional contributions. Monthly mode includes only "
        "whole calendar months within the selected dates.",

    "Risk versus return":
        "Annualised volatility = sample standard deviation × square root "
        "of periods per year. Compound annual growth = product of "
        "(1 + return), raised to periods per year / observations, minus 1. "
        "Uses 252 periods for daily data or 12 for monthly data. "
        "Annualising short samples can produce extreme results.",

    "Industry correlations":
        "The chart uses Pearson correlation of sector returns. "
        "Monthly returns are compounded from daily returns. "
        "Correlations can change over time and do not guarantee "
        "protection against losses.",

    "Return distributions":
        "The tail cutoff is a historical lower quantile. At 95% confidence, "
        "it is the fifth percentile. Tail mean is the average return "
        "at or below that cutoff. The dashed red line is your selected "
        "loss threshold; the dotted red line marks the histogram tail cutoff. "
        "These describe the historical sample rather than future losses."
}


def chart_explanation(chart_type):
    explanations = {
        "Histogram":
            "Bars show return density: their total area is 1. "
            "The smooth curve estimates the distribution. The optional "
            "normal reference uses the sample mean and standard deviation.",

        "Box plot":
            "The box contains the middle 50% of returns, with the median "
            "inside it. Whiskers extend to observations within "
            "1.5 interquartile ranges; more distant observations "
            "appear as separate points.",

        "Violin plot":
            "Wider sections indicate more concentrated returns. "
            "The internal box summarises the median and quartiles.",

        "Cumulative probability":
            "The height gives the proportion of historical returns "
            "at or below the value on the horizontal axis.",

        "Normal Q-Q":
            "Observed returns are compared with normal-distribution "
            "quantiles. Departures from the reference line indicate "
            "differences from a normal distribution."
    }

    return explanations[chart_type]


# --------------------------------------------------
# PREPARE RETURNS
# --------------------------------------------------

def prepare_returns(sectors, start_date, end_date, frequency):
    if not sectors:
        raise ValueError("Choose at least one sector.")

    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")

    if pd.isna(start) or pd.isna(end):
        raise ValueError("Enter dates as YYYY-MM-DD.")

    if start > end:
        raise ValueError("Choose a start date before the end date.")

    if frequency == "Monthly":
        # Compound daily decimal returns within each month
        monthly = (
            (1 + df[sectors])
            .resample("ME")
            .prod(min_count=1)
            - 1
        )

        # Keep months containing missing daily returns as missing
        missing = df[sectors].isna().resample("ME").sum()
        monthly = monthly.mask(missing > 0)

        # Include only whole calendar months within the selection
        month_starts = monthly.index.to_period("M").to_timestamp()

        returns = monthly.loc[
            (month_starts >= start) & (monthly.index <= end)
        ]

    else:
        returns = df.loc[start:end, sectors]

    # Compare sectors using common complete observations
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

    if returns.empty:
        raise ValueError(
            "There are no observations. Choose a longer period."
        )

    return returns


# --------------------------------------------------
# COMMON CHART STYLING
# --------------------------------------------------

def style_chart(fig, height=560, preview=False):
    fig.update_layout(
        template="plotly_white",
        height=height,
        autosize=True,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Arial, sans-serif",
            "size": 12,
            "color": NAVY
        },
        margin={
            "l": 55,
            "r": 25,
            "t": 80,
            "b": 70
        },
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.20,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11}
        },
        hoverlabel={
            "bgcolor": "white",
            "font_size": 12
        }
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#CBD5E1",
        automargin=True
    )

    fig.update_yaxes(
        gridcolor="#E8EDF3",
        zeroline=False,
        automargin=True
    )

    if preview:
        fig.update_layout(
            title=None,
            showlegend=False,
            font={"size": 10},
            margin={
                "l": 45,
                "r": 15,
                "t": 25,
                "b": 45
            }
        )

    return fig


def add_period(fig, returns, frequency):
    first = returns.index.min().strftime("%d %b %Y")
    last = returns.index.max().strftime("%d %b %Y")

    fig.update_layout(
        title={
            "text": (
                f"{frequency} returns · {first} – {last}"
                f"<br><sup>{len(returns):,} observations per sector</sup>"
            ),
            "font": {"size": 13},
            "x": 0.02,
            "y": 0.98
        }
    )


# --------------------------------------------------
# INVESTMENT GROWTH
# --------------------------------------------------

def growth_figure(returns, investment):
    growth = investment * (1 + returns).cumprod()

    # Add the initial investment before the first return
    baseline = pd.DataFrame(
        investment,
        index=[returns.index.min() - pd.Timedelta(days=1)],
        columns=returns.columns
    )

    growth = pd.concat([baseline, growth])

    fig = go.Figure()

    for sector in growth.columns:
        fig.add_trace(
            go.Scatter(
                x=growth.index,
                y=growth[sector],
                mode="lines",
                name=sector,
                line={
                    "color": PALETTE.get(sector, NAVY),
                    "width": 2.3
                },
                hovertemplate=(
                    "%{x|%d %b %Y}<br>"
                    "$%{y:,.2f}"
                    "<extra>%{fullData.name}</extra>"
                )
            )
        )

    fig.add_hline(
        y=investment,
        line_dash="dot",
        line_color="#94A3B8",
        line_width=1
    )

    fig.update_layout(
        hovermode="x unified",
        yaxis_title="Investment value ($)"
    )

    return fig


# --------------------------------------------------
# RISK VERSUS RETURN
# --------------------------------------------------

def risk_figure(returns, frequency):
    if len(returns) < 3:
        raise ValueError("Choose at least three observations.")

    periods = 252 if frequency == "Daily" else 12

    volatility = returns.std() * np.sqrt(periods) * 100

    annual_growth = (
        (1 + returns).prod() ** (periods / len(returns)) - 1
    ) * 100

    fig = go.Figure()

    for sector in returns.columns:
        fig.add_trace(
            go.Scatter(
                x=[volatility[sector]],
                y=[annual_growth[sector]],
                mode="markers+text",
                text=[sector],
                textposition="top center",
                name=sector,
                marker={
                    "size": 15,
                    "color": PALETTE.get(sector, NAVY),
                    "line": {
                        "color": "white",
                        "width": 1.5
                    }
                },
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Annualised volatility: %{x:.2f}%<br>"
                    "Compound annual growth: %{y:.2f}%"
                    "<extra></extra>"
                )
            )
        )

    fig.add_hline(
        y=0,
        line_color="#94A3B8",
        line_width=1
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Annualised volatility (%)",
        yaxis_title="Compound annual growth (%)"
    )

    # Leave space around sector labels
    xmin, xmax = volatility.min(), volatility.max()
    ymin, ymax = annual_growth.min(), annual_growth.max()

    xpad = max((xmax - xmin) * 0.25, 1)
    ypad = max((ymax - ymin) * 0.25, 1)

    fig.update_xaxes(
        range=[max(0, xmin - xpad), xmax + xpad]
    )

    fig.update_yaxes(
        range=[ymin - ypad, ymax + ypad]
    )

    return fig


# --------------------------------------------------
# CORRELATIONS
# --------------------------------------------------

def correlation_figure(returns):
    if len(returns.columns) < 2:
        raise ValueError("Choose at least two sectors.")

    if len(returns) < 3:
        raise ValueError("Choose at least three observations.")

    if (returns.nunique() < 2).any():
        raise ValueError("Choose a period with varying returns.")

    correlations = returns.corr()

    fig = go.Figure(
        go.Heatmap(
            z=correlations.to_numpy(),
            x=correlations.columns,
            y=correlations.index,
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale=[
                [0, "#B84A42"],
                [0.5, "#F8FAFC"],
                [1, "#245A91"]
            ],
            text=correlations.to_numpy(),
            texttemplate="%{text:.2f}",
            textfont={"size": 11},
            xgap=2,
            ygap=2,
            colorbar={"title": "Correlation"},
            hovertemplate=(
                "%{x} / %{y}<br>"
                "Correlation: %{z:.3f}<extra></extra>"
            )
        )
    )

    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(autorange="reversed")

    return fig


# --------------------------------------------------
# RETURN DISTRIBUTIONS
# --------------------------------------------------

def distribution_figure(
    returns,
    frequency,
    chart_type,
    bins,
    show_curve,
    show_normal,
    show_tail,
    confidence,
    loss_threshold
):
    if len(returns) < 3:
        raise ValueError(
            "Choose at least three observations per sector."
        )

    percentage_returns = returns * 100
    sectors = list(returns.columns)
    alpha = 1 - confidence / 100

    if chart_type in ["Histogram", "Normal Q-Q"]:
        columns = 1 if len(sectors) == 1 else 2
        rows = (len(sectors) + columns - 1) // columns

        fig = make_subplots(
            rows=rows,
            cols=columns,
            subplot_titles=sectors,
            shared_xaxes="all",
            shared_yaxes="all",
            vertical_spacing=0.12 if rows > 1 else 0
        )

        # Identical bin edges allow fair comparisons
        edges = np.histogram_bin_edges(
            percentage_returns.to_numpy().ravel(),
            bins=int(bins)
        )

        for i, sector in enumerate(sectors):
            row = i // columns + 1
            column = i % columns + 1

            values = percentage_returns[sector].to_numpy()
            colour = PALETTE.get(sector, NAVY)

            if chart_type == "Normal Q-Q":
                quantiles, fitted = stats.probplot(
                    values,
                    dist="norm"
                )

                theoretical, observed = quantiles
                slope, intercept, correlation = fitted

                fig.add_trace(
                    go.Scatter(
                        x=theoretical,
                        y=observed,
                        mode="markers",
                        name=sector,
                        showlegend=False,
                        marker={
                            "color": colour,
                            "size": 5,
                            "opacity": 0.65
                        },
                        hovertemplate=(
                            "Normal quantile: %{x:.2f}<br>"
                            "Observed return: %{y:.2f}%"
                            "<extra></extra>"
                        )
                    ),
                    row=row,
                    col=column
                )

                fig.add_trace(
                    go.Scatter(
                        x=theoretical,
                        y=slope * theoretical + intercept,
                        mode="lines",
                        name="Normal reference",
                        showlegend=(i == 0),
                        line={
                            "color": NAVY,
                            "dash": "dash",
                            "width": 1.5
                        },
                        hoverinfo="skip"
                    ),
                    row=row,
                    col=column
                )

                xlabel = "Theoretical normal quantile"
                ylabel = f"{frequency} return (%)"

            else:
                density, _ = np.histogram(
                    values,
                    bins=edges,
                    density=True
                )

                centres = (edges[:-1] + edges[1:]) / 2

                fig.add_trace(
                    go.Bar(
                        x=centres,
                        y=density,
                        width=np.diff(edges),
                        name=sector,
                        showlegend=False,
                        marker={
                            "color": colour,
                            "line": {
                                "color": "white",
                                "width": 0.7
                            }
                        },
                        opacity=0.85,
                        customdata=np.column_stack([
                            edges[:-1],
                            edges[1:]
                        ]),
                        hovertemplate=(
                            "Return bin: %{customdata[0]:.2f}%"
                            " to %{customdata[1]:.2f}%<br>"
                            "Density: %{y:.4f}<extra></extra>"
                        )
                    ),
                    row=row,
                    col=column
                )

                x = np.linspace(edges[0], edges[-1], 300)

                if show_curve and np.unique(values).size > 1:
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=stats.gaussian_kde(values)(x),
                            mode="lines",
                            name="Density curve",
                            showlegend=(i == 0),
                            line={
                                "color": NAVY,
                                "width": 2
                            },
                            hoverinfo="skip"
                        ),
                        row=row,
                        col=column
                    )

                if show_normal and values.std(ddof=1) > 0:
                    normal_density = stats.norm.pdf(
                        x,
                        loc=values.mean(),
                        scale=values.std(ddof=1)
                    )

                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=normal_density,
                            mode="lines",
                            name="Normal reference",
                            showlegend=(i == 0),
                            line={
                                "color": "#64748B",
                                "dash": "dash",
                                "width": 1.5
                            },
                            hoverinfo="skip"
                        ),
                        row=row,
                        col=column
                    )

                if show_tail:
                    cutoff = np.quantile(values, alpha)
                    tail_mean = values[values <= cutoff].mean()

                    fig.add_vrect(
                        x0=edges[0],
                        x1=cutoff,
                        fillcolor=RED,
                        opacity=0.10,
                        line_width=0,
                        row=row,
                        col=column
                    )

                    fig.add_vline(
                        x=cutoff,
                        line_color=RED,
                        line_dash="dot",
                        line_width=1.5,
                        row=row,
                        col=column
                    )

                    axis_number = i + 1

                    xref = (
                        "x domain"
                        if i == 0
                        else f"x{axis_number} domain"
                    )

                    yref = (
                        "y domain"
                        if i == 0
                        else f"y{axis_number} domain"
                    )

                    fig.add_annotation(
                        x=0.98,
                        y=0.98,
                        xref=xref,
                        yref=yref,
                        text=(
                            f"Cutoff: {cutoff:.2f}%<br>"
                            f"Tail mean: {tail_mean:.2f}%"
                        ),
                        showarrow=False,
                        xanchor="right",
                        yanchor="top",
                        font={
                            "size": 10,
                            "color": RED
                        },
                        bgcolor="rgba(255,255,255,0.85)"
                    )

                fig.add_vline(
                    x=loss_threshold,
                    line_color=RED,
                    line_dash="dash",
                    line_width=1.2,
                    row=row,
                    col=column
                )

                xlabel = f"{frequency} return (%)"
                ylabel = "Density"

            fig.update_xaxes(
                title_text=xlabel,
                row=row,
                col=column
            )

            fig.update_yaxes(
                title_text=ylabel,
                row=row,
                col=column
            )

        fig.update_layout(bargap=0)

    elif chart_type == "Cumulative probability":
        fig = go.Figure()

        for sector in sectors:
            values = np.sort(
                percentage_returns[sector].to_numpy()
            )

            probabilities = (
                np.arange(1, len(values) + 1) / len(values)
            )

            fig.add_trace(
                go.Scatter(
                    x=values,
                    y=probabilities,
                    mode="lines",
                    name=sector,
                    line={
                        "color": PALETTE.get(sector, NAVY),
                        "width": 2,
                        "shape": "hv"
                    },
                    hovertemplate=(
                        "Return: %{x:.2f}%<br>"
                        "At or below: %{y:.1%}"
                        "<extra>%{fullData.name}</extra>"
                    )
                )
            )

        fig.add_vline(
            x=loss_threshold,
            line_color=RED,
            line_dash="dash"
        )

        if show_tail:
            fig.add_hline(
                y=alpha,
                line_color="#64748B",
                line_dash="dot"
            )

        fig.update_layout(
            xaxis_title=f"{frequency} return (%)",
            yaxis_title="Proportion at or below return"
        )

        fig.update_yaxes(
            range=[0, 1],
            tickformat=".0%"
        )

    else:
        fig = go.Figure()

        for sector in sectors:
            values = percentage_returns[sector]
            colour = PALETTE.get(sector, NAVY)

            options = {
                "x": values,
                "name": sector,
                "orientation": "h",
                "line": {"color": colour},
                "fillcolor": colour,
                "opacity": 0.75,
                "showlegend": False
            }

            if chart_type == "Box plot":
                fig.add_trace(
                    go.Box(
                        **options,
                        boxpoints="outliers",
                        quartilemethod="linear"
                    )
                )

            else:
                if values.nunique() < 2:
                    raise ValueError(
                        "Choose a period with varying returns "
                        "for the violin plot."
                    )

                fig.add_trace(
                    go.Violin(
                        **options,
                        box_visible=True,
                        points=False,
                        spanmode="hard"
                    )
                )

            if show_tail:
                cutoff = values.quantile(alpha)
                tail_mean = values[values <= cutoff].mean()

                fig.add_trace(
                    go.Scatter(
                        x=[cutoff],
                        y=[sector],
                        mode="markers",
                        name="Tail cutoff",
                        showlegend=(sector == sectors[0]),
                        marker={
                            "color": RED,
                            "symbol": "diamond",
                            "size": 9
                        },
                        hovertemplate=(
                            "Tail cutoff: %{x:.2f}%"
                            "<extra></extra>"
                        )
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=[tail_mean],
                        y=[sector],
                        mode="markers",
                        name="Tail mean",
                        showlegend=(sector == sectors[0]),
                        marker={
                            "color": NAVY,
                            "symbol": "x",
                            "size": 9
                        },
                        hovertemplate=(
                            "Tail mean: %{x:.2f}%"
                            "<extra></extra>"
                        )
                    )
                )

        fig.add_vline(
            x=0,
            line_color="#94A3B8",
            line_width=1
        )

        fig.add_vline(
            x=loss_threshold,
            line_color=RED,
            line_dash="dash"
        )

        fig.update_xaxes(
            title_text=f"{frequency} return (%)"
        )

        fig.update_yaxes(
            categoryorder="array",
            categoryarray=sectors,
            autorange="reversed"
        )

    return fig


# --------------------------------------------------
# SIMPLIFIED DISTRIBUTION PREVIEW
# --------------------------------------------------

def distribution_preview_figure(returns):
    # A single density comparison is clearer in a small preview
    fig = go.Figure()
    percentages = returns * 100

    low = percentages.min().min()
    high = percentages.max().max()
    x = np.linspace(low, high, 350)

    for sector in returns.columns:
        values = percentages[sector].to_numpy()

        if len(values) >= 3 and np.unique(values).size > 1:
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=stats.gaussian_kde(values)(x),
                    mode="lines",
                    name=sector,
                    line={
                        "color": PALETTE.get(sector, NAVY),
                        "width": 2.2
                    },
                    hovertemplate=(
                        "Monthly return: %{x:.2f}%<br>"
                        "Density: %{y:.4f}"
                        "<extra>%{fullData.name}</extra>"
                    )
                )
            )

    fig.update_layout(
        xaxis_title="Monthly return (%)",
        yaxis_title="Density"
    )

    return fig


# --------------------------------------------------
# DRAW A DETAILED PANEL
# --------------------------------------------------

def draw_panel(
    panel,
    sectors,
    start_date,
    end_date,
    frequency,
    investment,
    chart_type,
    bins,
    show_curve,
    show_normal,
    show_tail,
    confidence,
    loss_threshold
):
    try:
        returns = prepare_returns(
            sectors,
            start_date,
            end_date,
            frequency
        )

        if panel == "Investment growth":
            if investment is None or investment <= 0:
                raise ValueError(
                    "Enter a positive starting investment."
                )

            fig = growth_figure(returns, investment)

        elif panel == "Risk versus return":
            fig = risk_figure(returns, frequency)

        elif panel == "Industry correlations":
            fig = correlation_figure(returns)

        else:
            if loss_threshold is None:
                raise ValueError("Enter a loss threshold.")

            fig = distribution_figure(
                returns,
                frequency,
                chart_type,
                bins,
                show_curve,
                show_normal,
                show_tail,
                confidence,
                loss_threshold
            )

        height = 560

        if panel == "Return distributions":
            if chart_type in ["Histogram", "Normal Q-Q"]:
                columns = 1 if len(sectors) == 1 else 2
                rows = (len(sectors) + columns - 1) // columns
                height = max(520, 290 * rows + 120)

        style_chart(fig, height=height)
        add_period(fig, returns, frequency)

        return fig, ""

    except ValueError as error:
        return None, str(error)


# --------------------------------------------------
# DISTRIBUTION CONTROL VISIBILITY
# --------------------------------------------------

def update_distribution_controls(chart_type):
    histogram = chart_type == "Histogram"
    qq_graph = chart_type == "Normal Q-Q"

    return (
        gr.update(visible=histogram),
        gr.update(visible=not qq_graph),
        chart_explanation(chart_type)
    )


# --------------------------------------------------
# OVERVIEW PREVIEWS
# --------------------------------------------------

def load_overview():
    daily = prepare_returns(
        DEFAULT_SECTORS,
        FIRST_DATE,
        LAST_DATE,
        "Daily"
    )

    monthly = prepare_returns(
        DEFAULT_SECTORS,
        FIRST_DATE,
        LAST_DATE,
        "Monthly"
    )

    figures = [
        growth_figure(daily, 1000),
        risk_figure(daily, "Daily"),
        correlation_figure(monthly),
        distribution_preview_figure(monthly)
    ]

    # Every overview chart has the same height
    for fig in figures:
        style_chart(
            fig,
            height=340,
            preview=True
        )

    figures[2].update_traces(
        showscale=False,
        textfont={"size": 10}
    )

    return tuple(figures)


# --------------------------------------------------
# BUILD THE APPLICATION
# --------------------------------------------------

with gr.Blocks(
    title="Industry Performance Explorer",
    fill_width=True
) as demo:

    # OVERVIEW PAGE
    with gr.Column(
        visible=True,
        min_width=0
    ) as overview:

        gr.Markdown("# Industry Performance Explorer")

        gr.Markdown(
            "### Growth. Risk. Diversification.\n"
            "How do industries compare? Open an analysis to "
            "explore its sectors, period and assumptions."
        )

        preview_plots = []
        explore_buttons = []

        # Two rows, with two equal-width panels in each row
        for pair in [PANELS[:2], PANELS[2:]]:

            with gr.Row(equal_height=True):

                for panel in pair:

                    with gr.Column(
                        scale=1,
                        min_width=0
                    ):
                        # One grey group connects each title, chart and button
                        with gr.Group():

                            gr.Markdown(
                                f"## {panel}\n"
                                f"{PREVIEW_DESCRIPTIONS[panel]}"
                            )

                            preview_plots.append(
                                gr.Plot(
                                    show_label=False,
                                    container=False
                                )
                            )

                            with gr.Row():
                                explore_buttons.append(
                                    gr.Button(
                                        f"Explore {panel.lower()} →",
                                        variant="primary",
                                        size="sm",
                                        scale=0,
                                        min_width=180
                                    )
                                )

        with gr.Accordion(
            "Data and methodology",
            open=False
        ):
            gr.Markdown(
                """
**Source:** Kenneth French 49 Industry Portfolios,
value-weighted daily returns.

**Custom sectors:** selected industry portfolios are combined
with equal weights within each custom sector. These are
project-defined groupings rather than official sector indices.

**Units:** the cleaned CSV stores decimal returns.
Charts display percentages where appropriate.

**Monthly returns:** calculated by compounding daily returns.
Only whole calendar months inside the selected dates are included.
Months containing missing daily returns are excluded.

**Missing observations:** selected sectors are compared using
common complete observations.

**Coverage:** US industry portfolios. Historical results exclude
investment fees and taxes.
                """
            )

        gr.Markdown(
            f"**Data coverage:** {FIRST_DATE} — {LAST_DATE}"
        )

    detail_views = []
    back_buttons = []

    # DETAILED PAGES
    for panel in PANELS:

        is_distribution = panel == "Return distributions"
        is_growth = panel == "Investment growth"

        with gr.Column(
            visible=False,
            min_width=0
        ) as detail_view:

            detail_views.append(detail_view)

            with gr.Row():
                back_buttons.append(
                    gr.Button(
                        "← Back to overview",
                        variant="secondary",
                        size="sm",
                        scale=0,
                        min_width=160
                    )
                )

            gr.Markdown(f"# {panel}")
            gr.Markdown(DESCRIPTIONS[panel])

            with gr.Row(equal_height=False):

                # GREY BOX 1: CONTROLS
                with gr.Column(
                    scale=1,
                    min_width=260
                ):
                    with gr.Group():

                        gr.Markdown(
                            "## Controls\n"
                            "These settings apply to the graph alongside."
                        )

                        sectors_input = gr.Dropdown(
                            choices=SECTORS,
                            value=DEFAULT_SECTORS,
                            multiselect=True,
                            label="Sectors",
                            container=False
                        )

                        frequency_input = gr.Radio(
                            choices=["Daily", "Monthly"],
                            value=(
                                "Monthly"
                                if panel in [
                                    "Industry correlations",
                                    "Return distributions"
                                ]
                                else "Daily"
                            ),
                            label="Return frequency",
                            container=False
                        )

                        chart_input = gr.Dropdown(
                            choices=CHART_TYPES,
                            value="Histogram",
                            label="Chart type",
                            visible=is_distribution,
                            container=False
                        )

                        gr.Markdown("### Selected period")

                        start_input = gr.Textbox(
                            value=FIRST_DATE,
                            label="Start date",
                            placeholder="YYYY-MM-DD",
                            container=False
                        )

                        end_input = gr.Textbox(
                            value=LAST_DATE,
                            label="End date",
                            placeholder="YYYY-MM-DD",
                            container=False
                        )

                        investment_input = gr.Number(
                            value=1000,
                            minimum=1,
                            label="Starting investment ($)",
                            visible=is_growth,
                            container=False
                        )

                        # Hide this entire section for Q-Q plots
                        with gr.Accordion(
                            "Downside analysis",
                            open=False,
                            visible=is_distribution
                        ) as downside_settings:

                            loss_input = gr.Number(
                                value=-5,
                                minimum=-30,
                                maximum=0,
                                step=0.5,
                                label="Loss threshold (%)",
                                container=False
                            )

                            tail_input = gr.Checkbox(
                                value=True,
                                label="Show downside tail",
                                container=False
                            )

                            confidence_input = gr.Slider(
                                minimum=90,
                                maximum=99,
                                value=95,
                                step=1,
                                label="Tail confidence (%)",
                                container=False
                            )

                        with gr.Accordion(
                            "Histogram settings",
                            open=False,
                            visible=is_distribution
                        ) as histogram_settings:

                            bins_input = gr.Slider(
                                minimum=10,
                                maximum=100,
                                value=30,
                                step=5,
                                label="Number of bins",
                                container=False
                            )

                            curve_input = gr.Checkbox(
                                value=True,
                                label="Density curve",
                                container=False
                            )

                            normal_input = gr.Checkbox(
                                value=False,
                                label="Normal reference",
                                container=False
                            )

                with gr.Column(
                    scale=4,
                    min_width=0
                ):

                    # GREY BOX 2: GRAPH
                    with gr.Group():

                        gr.Markdown(f"## Graph · {panel}")

                        message = gr.Markdown()

                        graph = gr.Plot(
                            show_label=False,
                            container=False
                        )

                        gr.Markdown(
                            "Hover for values · Drag to zoom · "
                            "Double-click to reset"
                        )

                    # GREY BOX 3: EXPLANATION
                    with gr.Group():

                        gr.Markdown("## Understanding this graph")

                        explanation = gr.Markdown(
                            chart_explanation("Histogram")
                            if is_distribution
                            else READING_GUIDES[panel]
                        )

                        with gr.Accordion(
                            "Calculations and assumptions",
                            open=False
                        ):
                            gr.Markdown(METHODS[panel])

                            gr.Markdown(
                                "Historical performance does not "
                                "predict future returns."
                            )

            # Identify the calculation used by this detailed page
            panel_input = gr.State(panel)

            inputs = [
                panel_input,
                sectors_input,
                start_input,
                end_input,
                frequency_input,
                investment_input,
                chart_input,
                bins_input,
                curve_input,
                normal_input,
                tail_input,
                confidence_input,
                loss_input
            ]

            outputs = [graph, message]

            # Draw the initial detailed graph
            demo.load(
                fn=draw_panel,
                inputs=inputs,
                outputs=outputs,
                concurrency_id="charts",
                concurrency_limit=1
            )

            # Redraw automatically when any setting changes
            for control in inputs[1:]:
                control.change(
                    fn=draw_panel,
                    inputs=inputs,
                    outputs=outputs,
                    trigger_mode="always_last",
                    concurrency_id="charts",
                    concurrency_limit=1
                )

            if is_distribution:
                chart_input.change(
                    fn=update_distribution_controls,
                    inputs=chart_input,
                    outputs=[
                        histogram_settings,
                        downside_settings,
                        explanation
                    ],
                    queue=False
                )

    # NAVIGATION
    views = [overview] + detail_views

    def show_view(index):
        return [
            gr.update(visible=(i == index))
            for i in range(len(views))
        ]

    def navigation_action(index):
        # Capture the correct destination for each button
        def action():
            return show_view(index)

        return action

    for index, button in enumerate(
        explore_buttons,
        start=1
    ):
        button.click(
            fn=navigation_action(index),
            outputs=views,
            queue=False
        )

    for button in back_buttons:
        button.click(
            fn=navigation_action(0),
            outputs=views,
            queue=False
        )

    # Overview previews remain fixed when detailed settings change
    demo.load(
        fn=load_overview,
        outputs=preview_plots,
        concurrency_id="charts",
        concurrency_limit=1
    )


# --------------------------------------------------
# START THE APP
# --------------------------------------------------

if __name__ == "__main__":

    # Style everything using Gradio's Python theme API
    theme = gr.themes.Base(
        primary_hue="slate",
        secondary_hue="blue",
        neutral_hue="slate",
        spacing_size="lg",
        radius_size="md",
        text_size="md"
    ).set(
        body_background_fill="#FFFFFF",
        body_background_fill_dark="#FFFFFF",
        background_fill_primary="#FFFFFF",
        background_fill_primary_dark="#FFFFFF",
        background_fill_secondary="#F1F4F8",
        background_fill_secondary_dark="#F1F4F8",
        block_background_fill="#F1F4F8",
        block_background_fill_dark="#F1F4F8",
        block_border_width="1px",
        block_border_color="#DEE5EE",
        block_border_color_dark="#DEE5EE",
        block_shadow="none",
        body_text_color="#17283E",
        body_text_color_dark="#17283E",
        body_text_color_subdued="#526174",
        body_text_color_subdued_dark="#526174",
        block_title_text_color="#17283E",
        block_title_text_color_dark="#17283E",
        block_label_text_color="#334155",
        block_label_text_color_dark="#334155",
        input_background_fill="#FFFFFF",
        input_background_fill_dark="#FFFFFF",
        input_border_color="#D5DEEA",
        input_border_color_dark="#D5DEEA",
        button_primary_background_fill="#17283E",
        button_primary_background_fill_dark="#17283E",
        button_primary_text_color="#FFFFFF",
        button_primary_text_color_dark="#FFFFFF",
        button_secondary_background_fill="#E5EBF3",
        button_secondary_background_fill_dark="#E5EBF3",
        button_secondary_text_color="#17283E",
        button_secondary_text_color_dark="#17283E"
    )

    demo.launch(
        inbrowser=True,
        theme=theme
    )