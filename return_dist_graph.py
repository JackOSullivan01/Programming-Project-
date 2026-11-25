from pathlib import Path
import base64
from scipy import stats

import gradio as gr
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager


# Load the cleaned dataset
filename = Path(__file__).parent / "industry_returns_clean.csv"

df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
).sort_index()

#Use the same sector colours across every graph
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


#Apply consistent styling
def style_figure(fig):
    fig.set_facecolor("white")

    for ax in fig.axes:
        if not ax.get_visible():
            continue

        ax.set_facecolor("white")
        ax.set_axisbelow(True)

        #Keep subtle horizontal gridlines
        ax.grid(axis="y", color="#E4E9EF", linewidth=0.7)
        ax.grid(axis="x", visible=False)

        #Remove unnecessary borders
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#D4DCE5")

        #Style labels and titles
        ax.tick_params(
            axis="both",
            labelsize=9,
            colors="#637084",
            length=0,
            pad=6
        )

        ax.xaxis.label.set_color("#637084")
        ax.yaxis.label.set_color("#637084")
        ax.title.set_color("#17283E")
        ax.title.set_fontweight("bold")

        #Keep legends light and compact
        legend = ax.get_legend()

        if legend is not None:
            legend.set_frame_on(False)

            for text in legend.get_texts():
                text.set_fontsize(8)
                text.set_color("#17283E")

# Show the period and number of observations used in the graph
def add_graph_details(fig, returns, frequency):
    first_date = returns.index.min().strftime("%d %b %Y")
    last_date = returns.index.max().strftime("%d %b %Y")

    counts = returns.count()
    smallest_count = int(counts.min())
    largest_count = int(counts.max())

    if smallest_count == largest_count:
        observation_text = f"{smallest_count:,} observations per sector"
    else:
        observation_text = (
            f"{smallest_count:,}–{largest_count:,} observations per sector"
        )

    fig.suptitle(
        f"{frequency} returns  ·  {first_date} – {last_date}  ·  {observation_text}",
        fontsize=8,
        color="#526174"
    )


def parse_input_date(value):
    # Irish input dates use day/month/year. ISO remains accepted for callers.
    text = str(value).strip()
    date_format = "%Y-%m-%d" if "-" in text else "%d/%m/%Y"
    return pd.to_datetime(text, format=date_format, errors="coerce")


# Gradio runs this function whenever an input changes
def draw_histogram(
        sector, start_date, end_date, bins, frequency, loss_threshold,
        show_curve, show_normal, show_tail, confidence, chart_type,
        view_range="Central 98%", show_loss=False
):

    if not sector:
        return None, "Choose at least one sector."

    # Convert the text inputs into dates
    start = parse_input_date(start_date)
    end = parse_input_date(end_date)

    # Check the dates are valid
    if pd.isna(start) or pd.isna(end):
        return None, "Enter dates as DD/MM/YYYY, for example 24/11/2026."

    if start > end:
        return None, "Choose a start date before the end date."

    if frequency == "Monthly":
        #Compound daily decimal returns within each month
        monthly = (1 + df[sector]).resample("ME").prod(min_count=1) - 1

        #Keep months containing missing daily returns as missing
        missing = df[sector].isna().resample("ME").sum()
        monthly = monthly.mask(missing > 0)

        #Use only whole calendar months inside the selected dates
        month_starts = monthly.index.to_period("M").to_timestamp()

        sector_returns = monthly.loc[
            (month_starts >= start) & (monthly.index <= end)
    ].dropna() * 100

    else:
        #Select daily returns within the chosen dates
        sector_returns = df.loc[start:end, sector].dropna() * 100

    if sector_returns.empty:
        return None, "There are no observations in this period."

    # Check there is enough data for the selected graph
    observation_counts = sector_returns.count()

    minimum_observations = 1

    if chart_type == "Box plot":
        minimum_observations = 2

    elif chart_type in ["Violin plot", "Normal Q-Q"]:
        minimum_observations = 3

    insufficient = observation_counts[
        observation_counts < minimum_observations
    ].index.tolist()

    if insufficient:
        return None, (
            f"Choose a longer period for: {', '.join(insufficient)}. "
            f"This graph needs at least {minimum_observations} "
            "observations per sector."
        )

    # A violin needs variation to estimate a density
    if chart_type == "Violin plot":
        constant_sectors = [
            selected_sector
            for selected_sector in sector_returns.columns
            if sector_returns[selected_sector].dropna().nunique() < 2
        ]

        if constant_sectors:
            return None, (
                "Choose a period with varying returns for: "
                + ", ".join(constant_sectors)
                + "."
            )

    # Plotly changes rendering only: the selected returns above stay unchanged.
    return draw_interactive_distribution(
        sector_returns, bins, frequency, loss_threshold, show_curve,
        show_normal, show_tail, confidence, chart_type, view_range, show_loss
    )


def plain_plotly_values(value):
    if isinstance(value, dict):
        if "bdata" in value and "dtype" in value:
            array = np.frombuffer(
                base64.b64decode(value["bdata"]), dtype=np.dtype(value["dtype"])
            )
            shape = value.get("shape")
            if shape:
                dimensions = tuple(int(item.strip()) for item in shape.split(","))
                array = array.reshape(dimensions)
            return array.tolist()
        return {key: plain_plotly_values(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain_plotly_values(item) for item in value]
    if isinstance(value, np.ndarray):
        return plain_plotly_values(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def style_interactive_figure(fig, height=510):
    fig.update_layout(
        template="plotly_white", height=height, autosize=True,
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, sans-serif", size=12, color="#17283E"),
        margin=dict(l=65, r=28, t=40, b=85),
        hovermode="closest", dragmode="zoom",
        hoverlabel=dict(bgcolor="white", font_color="#17283E"),
        legend=dict(orientation="h", x=0, y=-0.18, font_size=11),
        uirevision=None
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#D4DCE5",
                     automargin=True, fixedrange=False)
    fig.update_yaxes(gridcolor="#E4E9EF", zeroline=False,
                     automargin=True, fixedrange=False)
    return fig


def distribution_statistics(returns, confidence, loss_threshold):
    # Use the exact same percentage returns as the charts, before display cropping.
    alpha = 1 - confidence / 100
    records = []
    valid_threshold = loss_threshold is not None and np.isfinite(loss_threshold)
    for name in returns.columns:
        values = returns[name].dropna()
        q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
        cutoff = values.quantile(alpha)
        record = {
            "sector": name,
            "median": float(median),
            "iqr": float(q3 - q1),
            "cutoff": float(cutoff),
            "tail_mean": float(values[values <= cutoff].mean()),
            "observations": int(len(values))
        }
        if valid_threshold:
            record["loss_rate"] = float((values <= loss_threshold).mean() * 100)
            record["loss_count"] = int((values <= loss_threshold).sum())
        records.append(record)
    return records


def sample_findings(records, frequency, confidence, loss_threshold, chart_type):
    # Rankings use unrounded numbers and report tied sectors together.
    table = pd.DataFrame(records).set_index("sector")
    period = "daily" if frequency == "Daily" else "monthly"
    count = int(table["observations"].min())

    def names_at(column, value):
        matches = np.isclose(table[column].to_numpy(), value, rtol=1e-9, atol=1e-10)
        return ", ".join(str(name) for name in table.index[matches])

    widest, narrowest = float(table["iqr"].max()), float(table["iqr"].min())
    if len(table) == 1:
        spread = (
            f"**Spread:** {table.index[0]}'s middle 50% of {period} returns "
            f"span **{widest:.2f} percentage points**."
        )
    elif np.isclose(widest, narrowest):
        spread = (
            f"**Spread:** the selected sectors have the same middle-50% range "
            f"of **{widest:.2f} percentage points**."
        )
    else:
        spread = (
            f"**Spread:** {names_at('iqr', widest)} had the widest middle-50% "
            f"range (**{widest:.2f} pp**); {names_at('iqr', narrowest)} had "
            f"the narrowest (**{narrowest:.2f} pp**)."
        )

    lowest_tail = float(table["tail_mean"].min())
    tail_names = names_at("tail_mean", lowest_tail)
    tail = (
        f"**Downside:** {tail_names} had "
        f"{'a' if len(table) == 1 else 'the lowest'} historical tail mean "
        f"of **{lowest_tail:.2f}%**. This averages returns at or below each "
        f"sector's lower **{100-confidence:g}% cutoff**."
    )

    lines = [spread, tail]
    if "loss_rate" in table:
        maximum_rate = float(table["loss_rate"].max())
        if maximum_rate == 0:
            loss = (
                f"**Loss frequency:** no selected sector had a {period} return "
                f"at or below **{loss_threshold:g}%** in this sample."
            )
        else:
            loss = (
                f"**Loss frequency:** {names_at('loss_rate', maximum_rate)} "
                f"{'recorded returns' if len(table) == 1 else 'most often recorded returns'} "
                f"at or below **{loss_threshold:g}%** "
                f"(**{maximum_rate:.1f}%** of observations)."
            )
        lines.append(loss)

    if chart_type == "Normal Q-Q":
        lines.append(
            "**Q-Q interpretation:** these numerical summaries do not test normality. "
            "Use departures of the plotted points from the normal reference line "
            "to assess how the sample differs from that reference."
        )
    if count < 20:
        lines.append(
            f"This sample contains only **{count} observations per sector**; "
            "distribution and tail comparisons are particularly sensitive to individual observations."
        )
    lines.append(
        f"Based on **{count:,} {period} observations per sector**. "
        "Uses the full selected sample, including observations outside a central histogram window. "
        "The confidence level and loss threshold come from the Risk controls, even when overlays are hidden. "
        "These are historical descriptions, not forecasts."
    )

    display = table.reset_index().rename(columns={
        "sector": "Sector", "median": "Median return (%)",
        "iqr": "Middle-50% range (pp)", "cutoff": "Tail cutoff (%)",
        "tail_mean": "Tail mean (%)"
    })
    columns = ["Sector", "Median return (%)", "Middle-50% range (pp)"]
    if "loss_rate" in table:
        loss_label = f"Returns ≤ {loss_threshold:g}% (%)"
        display = display.rename(columns={"loss_rate": loss_label})
        columns.append(loss_label)
    columns += ["Tail cutoff (%)", "Tail mean (%)"]
    display = display[columns].copy()
    for name in columns[1:]:
        display[name] = display[name].round(3)
    return "\n\n".join(lines), display


def draw_interactive_distribution(
    returns, bins, frequency, loss_threshold, show_curve, show_normal,
    show_tail, confidence, chart_type, view_range, show_loss
):
    # Returns are already percentages, prepared by the existing callback.
    sectors = list(returns.columns)
    alpha = 1 - confidence / 100
    tails = {}
    for name in sectors:
        values = returns[name].dropna()
        cutoff = float(values.quantile(alpha))
        tails[name] = {
            "cutoff": cutoff,
            "tail_mean": float(values[values <= cutoff].mean())
        }
    metadata = {
        "observations": len(returns), "tails": tails,
        "distribution_statistics": distribution_statistics(returns, confidence, loss_threshold)
    }
    message = ""

    if chart_type in ["Histogram", "Normal Q-Q"]:
        columns = 1 if len(sectors) == 1 else 2
        rows = (len(sectors) + columns - 1) // columns
        fig = make_subplots(
            rows=rows, cols=columns, subplot_titles=sectors,
            shared_xaxes="all", shared_yaxes="all",
            vertical_spacing=0.15 if rows > 1 else 0
        )
        height = max(450, rows * 250 + 100)

        if chart_type == "Histogram":
            all_values = returns.to_numpy().ravel()
            central = view_range == "Central 98%"
            low, high = np.quantile(all_values, [0.01, 0.99])
            if not central or low == high:
                low, high = all_values.min(), all_values.max()
            if low == high:
                low, high = low - 0.5, high + 0.5
            if central and show_loss:
                padding = max((high - low) * 0.025, 0.05)
                low = min(low, loss_threshold - padding)
                high = max(high, loss_threshold + padding)

            # Outer bins retain extreme observations in the normalisation.
            edges = np.linspace(low, high, int(bins) + 1)
            if all_values.min() < low:
                edges = np.r_[all_values.min(), edges]
            if all_values.max() > high:
                edges = np.r_[edges, all_values.max()]
            metadata["histogram_edges"] = edges.tolist()
            outside_messages = []
            maximum_density = 0.0

        for i, name in enumerate(sectors):
            row, col = i // columns + 1, i % columns + 1
            values = returns[name].dropna().to_numpy()
            colour = PALETTE.get(name, "#245A91")

            if chart_type == "Normal Q-Q":
                quantiles, fitted = stats.probplot(values, dist="norm")
                theoretical, observed = quantiles
                slope, intercept, correlation = fitted
                fig.add_trace(go.Scatter(
                    x=theoretical, y=observed, mode="markers", name=name,
                    showlegend=False, marker=dict(color=colour, size=5, opacity=0.7),
                    hovertemplate=("Normal quantile: %{x:.3f}<br>"
                                   "Observed return: %{y:.3f}%<extra>" + name + "</extra>")
                ), row=row, col=col)
                fig.add_trace(go.Scatter(
                    x=theoretical, y=slope * theoretical + intercept,
                    mode="lines", name="Normal reference", showlegend=(i == 0),
                    legendgroup="normal", line=dict(color="#637084", dash="dash"),
                    hovertemplate="Fitted normal return: %{y:.3f}%<extra></extra>"
                ), row=row, col=col)
                xlabel = "Theoretical normal quantile"
                ylabel = f"{frequency} return (%)"

            else:
                counts, _ = np.histogram(values, bins=edges)
                widths = np.diff(edges)
                density = counts / (len(values) * widths)
                maximum_density = max(maximum_density, float(density.max()))
                centres = (edges[:-1] + edges[1:]) / 2
                custom = np.column_stack([
                    edges[:-1], edges[1:], counts, counts / len(values)
                ])
                fig.add_trace(go.Bar(
                    x=centres, y=density, width=widths, name=name,
                    showlegend=False, marker=dict(color=colour,
                    line=dict(color="white", width=0.6)), opacity=0.9,
                    customdata=custom,
                    hovertemplate=("Bin: %{customdata[0]:.2f}% to %{customdata[1]:.2f}%"
                                   "<br>Observations: %{customdata[2]:.0f}"
                                   "<br>Sample share: %{customdata[3]:.2%}"
                                   "<br>Density: %{y:.4f}<extra>" + name + "</extra>")
                ), row=row, col=col)
                x = np.linspace(low, high, 500)
                if show_curve and len(values) >= 3 and np.unique(values).size > 1:
                    curve_density = stats.gaussian_kde(values)(x)
                    maximum_density = max(maximum_density, float(curve_density.max()))
                    fig.add_trace(go.Scatter(
                        x=x, y=curve_density, mode="lines",
                        name="Density curve", legendgroup="density", showlegend=(i == 0),
                        line=dict(color="#17345C", width=2),
                        hovertemplate="Return: %{x:.2f}%<br>Density: %{y:.4f}<extra>Density curve</extra>"
                    ), row=row, col=col)
                if show_normal and len(values) >= 3 and values.std(ddof=1) > 0:
                    normal_density = stats.norm.pdf(x, loc=values.mean(), scale=values.std(ddof=1))
                    maximum_density = max(maximum_density, float(normal_density.max()))
                    fig.add_trace(go.Scatter(
                        x=x, y=normal_density,
                        mode="lines", name="Normal reference", legendgroup="normal",
                        showlegend=(i == 0), line=dict(color="#637084", dash="dash"),
                        hovertemplate="Return: %{x:.2f}%<br>Density: %{y:.4f}<extra>Normal reference</extra>"
                    ), row=row, col=col)
                if show_tail:
                    cutoff, tail_mean = tails[name]["cutoff"], tails[name]["tail_mean"]
                    if cutoff > low:
                        fig.add_vrect(x0=low, x1=min(high, cutoff),
                                      fillcolor="#B84A42", opacity=0.1, line_width=0,
                                      row=row, col=col)
                    fig.add_vline(x=cutoff, line_color="#B84A42", line_dash="dot",
                                  line_width=1.5, row=row, col=col)
                    axis = "" if i == 0 else str(i + 1)
                    fig.add_annotation(
                        x=0.98, y=0.97, xref=f"x{axis} domain", yref=f"y{axis} domain",
                        text=f"Cutoff {cutoff:.2f}%<br>Tail mean {tail_mean:.2f}%",
                        showarrow=False, xanchor="right", yanchor="top",
                        font=dict(size=10, color="#B84A42"), bgcolor="rgba(255,255,255,0.85)"
                    )
                if show_loss:
                    fig.add_vline(x=loss_threshold, line_color="#DC2626", line_dash="dash",
                                  line_width=1.2, row=row, col=col)
                fig.update_xaxes(range=[low, high], row=row, col=col)
                xlabel, ylabel = f"{frequency} return (%)", "Density"
                if central:
                    outside = int(((values < low) | (values > high)).sum())
                    outside_messages.append(f"{name}: {outside:,} ({outside / len(values):.1%})")
            if row == rows:
                fig.update_xaxes(title_text=xlabel, row=row, col=col)
            if col == 1:
                fig.update_yaxes(title_text=ylabel, row=row, col=col)

        if chart_type == "Histogram":
            # Shared legend entries for reference lines drawn as shapes.
            if show_tail:
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                    name=f"Lower {100 - confidence:g}% cutoff",
                    line=dict(color="#B84A42", dash="dot")), row=1, col=1)
            if show_loss:
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                    name=f"Loss threshold {loss_threshold:g}%",
                    line=dict(color="#DC2626", dash="dash")), row=1, col=1)
            fig.update_layout(bargap=0)
            fig.update_yaxes(
                range=[0, max(maximum_density * 1.15, 0.001)],
                autorange=False, tickformat=".3f", nticks=5
            )
            if central:
                message = (
                    f"**Central 98% view:** shared limits {low:.2f}% to {high:.2f}% "
                    "start from the pooled first and 99th percentiles and expand if needed "
                    "to include the selected loss line. Observations outside the view: "
                    + "; ".join(outside_messages)
                    + ". No observations are removed from density or tail calculations. "
                    "Choose Full range to see the extremes."
                )

    elif chart_type == "Cumulative probability":
        fig = go.Figure()
        height = 500
        for name in sectors:
            values, counts = np.unique(returns[name].dropna().to_numpy(), return_counts=True)
            probabilities = np.cumsum(counts) / counts.sum()
            fig.add_trace(go.Scatter(
                x=values, y=probabilities, mode="lines", name=name,
                line=dict(color=PALETTE.get(name, "#245A91"), width=2, shape="hv"),
                hovertemplate="Return: %{x:.3f}%<br>At or below: %{y:.2%}<extra>" + name + "</extra>"
            ))
        if show_loss:
            fig.add_vline(x=loss_threshold, line_color="#DC2626", line_dash="dash")
        if show_tail:
            fig.add_hline(y=alpha, line_color="#637084", line_dash="dot")
        fig.update_xaxes(title_text=f"{frequency} return (%)")
        fig.update_yaxes(title_text="Proportion at or below return", tickformat=".0%", range=[0, 1])

    else:
        fig = go.Figure()
        height = max(450, len(sectors) * 44 + 120)
        for name in sectors:
            values = returns[name].dropna().to_numpy()
            colour = PALETTE.get(name, "#245A91")
            options = dict(x=values.tolist(), y=[name] * len(values),
                           name=name, orientation="h", showlegend=False,
                           line=dict(color=colour, width=1), fillcolor=colour, opacity=0.85)
            if chart_type == "Box plot":
                # Suppress Plotly's multi-label box hover and provide one summary.
                fig.add_trace(go.Box(
                    **options, quartilemethod="linear", boxpoints=False,
                    hoverinfo="skip", hoveron="points", width=0.5
                ))
                q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75])
                iqr = q3 - q1
                lower = float(values[values >= q1 - 1.5 * iqr].min())
                upper = float(values[values <= q3 + 1.5 * iqr].max())
                summary = (
                    f"<b>{name}</b><br>Observations: {len(values):,}"
                    f"<br>Lower whisker: {lower:.2f}%"
                    f"<br>Lower quartile: {q1:.2f}%"
                    f"<br>Median: {median:.2f}%"
                    f"<br>Upper quartile: {q3:.2f}%"
                    f"<br>Upper whisker: {upper:.2f}%<extra></extra>"
                )
                # Closely spaced invisible targets cover the box body for hover.
                fig.add_trace(go.Scatter(
                    x=np.linspace(q1, q3, 15).tolist(), y=[name] * 15,
                    mode="markers", showlegend=False,
                    marker=dict(size=22, color="rgba(0,0,0,0)"),
                    hovertemplate=summary, name=name
                ))
                outliers = values[(values < lower) | (values > upper)]
                if len(outliers):
                    fig.add_trace(go.Scatter(
                        x=outliers.tolist(), y=[name] * len(outliers),
                        mode="markers", showlegend=False, name=name,
                        marker=dict(size=4, color=colour, opacity=0.75),
                        hovertemplate="<b>" + name + "</b><br>Outlier: %{x:.2f}%<extra></extra>"
                    ))
            else:
                # Plotly draws the violin density; quartiles are supplied separately
                # below so their numerical values match the existing calculations.
                fig.add_trace(go.Violin(**options, points=False, spanmode="hard",
                                       box_visible=False, meanline_visible=False))
                q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75])
                fig.add_trace(go.Scatter(
                    x=[q1, median, q3], y=[name, name, name], mode="markers",
                    showlegend=False, marker=dict(color="#17283E", symbol="line-ns", size=13,
                                                  line=dict(color="#17283E", width=1.3)),
                    customdata=["Lower quartile", "Median", "Upper quartile"],
                    hovertemplate="%{customdata}: %{x:.3f}%<extra>" + name + "</extra>"
                ))
            if show_tail:
                for key, symbol, label, colour in [
                    ("cutoff", "diamond", f"Lower {100-confidence:g}% cutoff", "#B84A42"),
                    ("tail_mean", "x", "Tail mean", "#17283E")
                ]:
                    fig.add_trace(go.Scatter(
                        x=[tails[name][key]], y=[name], mode="markers", name=label,
                        legendgroup=key, showlegend=(name == sectors[0]),
                        marker=dict(color=colour, symbol=symbol, size=9),
                        hovertemplate=label + ": %{x:.3f}%<extra>" + name + "</extra>"
                    ))
        fig.add_vline(x=0, line_color="#94A3B8", line_width=0.8)
        if show_loss:
            fig.add_vline(x=loss_threshold, line_color="#DC2626", line_dash="dash")
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                name=f"Loss threshold {loss_threshold:g}%",
                line=dict(color="#DC2626", dash="dash")))
        fig.update_xaxes(title_text=f"{frequency} return (%)")
        fig.update_yaxes(type="category", categoryorder="array", categoryarray=sectors,
                         autorange="reversed", tickangle=0)

    style_interactive_figure(fig, height)
    fig.update_layout(meta=metadata)
    # Use ordinary lists for compatibility with Gradio's bundled Plotly renderer.
    # New Plotly versions otherwise encode NumPy arrays as binary typed arrays.
    fig = go.Figure(plain_plotly_values(fig.to_plotly_json()))
    return fig, message


# Explain the selected analysis without changing the graph calculations
def chart_explanation(chart_type):
    explanations = {
        "Histogram": "The full histogram has total area 1; a central-range view shows only part of that area. The smooth curve estimates the return distribution. The optional normal reference uses the sample mean and standard deviation.",
        "Box plot": "The box contains the middle 50% of returns and its centre line is the median. Whiskers extend to observations within 1.5 interquartile ranges; more distant observations appear separately.",
        "Violin plot": "Wider sections indicate more concentrated returns. Internal lines show the quartiles.",
        "Cumulative probability": "The curve gives the proportion of historical observations at or below each return.",
        "Normal Q-Q": "Observed returns are compared with theoretical normal quantiles. Departures from the reference line indicate differences from a normal distribution."
    }
    return explanations[chart_type]


# Generate a compact violin preview from the real monthly sector returns.
def make_distribution_preview():
    selected = [name for name in [
        "Technology", "Financials", "Healthcare", "Energy"
    ] if name in df.columns]
    if not selected:
        selected = list(df.columns[:4])

    monthly = (1 + df[selected]).resample("ME").prod(min_count=1) - 1
    missing = df[selected].isna().resample("ME").sum()
    monthly = monthly.mask(missing > 0).dropna() * 100

    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=150, layout="constrained")
    if len(monthly) < 3 or (monthly.nunique() < 2).any():
        ax.text(0.5, 0.5, "Not enough monthly data for a preview.",
                transform=ax.transAxes, ha="center")
        ax.set_axis_off()
    else:
        plot_data = monthly.melt(var_name="Sector", value_name="Return (%)")
        sns.violinplot(
            data=plot_data, x="Return (%)", y="Sector", order=selected,
            hue="Sector", palette=PALETTE, dodge=False, legend=False,
            inner="quart", cut=0, width=0.68, linewidth=0.7,
            saturation=1, ax=ax
        )
        ax.axvline(0, color="#94A3B8", linewidth=0.8, zorder=0)
        ax.set_xlabel("Monthly return (%)", fontsize=13, labelpad=8)
        ax.set_ylabel("")
        first = monthly.index.min().to_period("M").start_time.strftime("%b %Y")
        last = monthly.index.max().strftime("%b %Y")
        ax.set_title(f"Monthly returns · {first} – {last}",
                     loc="left", fontsize=12, pad=12)
    style_figure(fig)
    # Preview labels need to stay readable at half-page width.
    ax.tick_params(axis="y", labelsize=13, pad=8)
    ax.tick_params(axis="x", labelsize=11)
    ax.grid(False)
    ax.spines["bottom"].set_color("#DCE3EC")
    ax.title.set_fontweight("normal")
    plt.close(fig)
    return fig


# Chart-specific reading notes avoid histogram instructions on other views
def reading_notes(chart_type):
    notes = {
        "Histogram": "**Compare shape and spread.** Common axes and bin edges make the sector panels comparable. Density is not the probability of a single return.",
        "Box plot": "**Compare medians, spread and outliers.** Wider boxes mean a larger middle-50% range. Diamond markers identify tail cutoffs; crosses identify tail means when enabled.",
        "Violin plot": "**Compare concentration and asymmetry.** All sectors share a return axis. Wider sections indicate more concentrated returns; internal lines mark quartiles. Optional diamonds and crosses show tail cutoffs and means.",
        "Cumulative probability": "**Read probability vertically.** At any return, a higher curve means a larger fraction of observations at or below that value. The optional horizontal guide marks the selected lower-tail probability.",
        "Normal Q-Q": "**Look for departures from the line.** Systematic curves or large tail deviations suggest returns differ from the fitted normal reference. The horizontal axis contains normal quantiles, not return percentages."
    }
    return notes[chart_type]


def update_controls(chart_type):
    histogram = chart_type == "Histogram"
    return (
        gr.update(visible=histogram),
        gr.update(visible=chart_type != "Normal Q-Q"),
        chart_explanation(chart_type),
        gr.update(visible=histogram),
        reading_notes(chart_type),
        f"### {chart_type}"
    )


# Separate validation messages from histogram-only range information
def render_distribution(*inputs):
    empty_table = pd.DataFrame(columns=[
        "Sector", "Median return (%)", "Middle-50% range (pp)",
        "Tail cutoff (%)", "Tail mean (%)"
    ])
    if inputs[12] and (inputs[5] is None or not np.isfinite(inputs[5])):
        return None, "Enter a finite loss threshold, or turn its reference line off.", "", "", "", "", "", empty_table
    fig, text = draw_histogram(*inputs)
    if fig is None:
        # Clear old interpretations and tables when the selection is invalid.
        return None, text, "", "", "", "", "", empty_table
    findings, table = sample_findings(
        fig.layout.meta["distribution_statistics"], inputs[4], inputs[9],
        inputs[5], inputs[10]
    )
    # Separate the findings from the supporting notes without changing calculations.
    paragraphs = findings.split("\n\n")
    cards = []
    for label in ["Spread", "Downside", "Loss frequency"]:
        prefix = f"**{label}:** "
        cards.append(next((part[len(prefix):] for part in paragraphs
                           if part.startswith(prefix)), "Enter a valid loss threshold in Risk."))
    notes = "\n\n".join(part for part in paragraphs if not part.startswith(
        ("**Spread:**", "**Downside:**", "**Loss frequency:**")
    ))
    return fig, "", text, *cards, notes, table


def selection_summary(sectors, frequency, start_date, end_date):
    # Match the main dashboard's navy header, with a slimmer profile.
    width, height = 2200, 154
    image = Image.new("RGB", (width, height), "#17283E")
    draw = ImageDraw.Draw(image)
    bold_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    regular_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans")
    )
    draw.text(
        (width / 2, 43), "Return distributions",
        font=ImageFont.truetype(bold_path, 60),
        fill="#FFFFFF", anchor="mm"
    )
    draw.text(
        (width / 2, 88),
        "A clearer view of sector returns, from typical outcomes to tail risk.",
        font=ImageFont.truetype(regular_path, 25),
        fill="#CBD9E8", anchor="mm"
    )
    draw.text(
        (width / 2, 126),
        f"{len(sectors or [])} sectors  ·  {frequency} returns  ·  "
        f"{start_date} — {end_date}",
        font=ImageFont.truetype(regular_path, 24),
        fill="#7ED7CF", anchor="mm"
    )
    return image


def make_controls_banner():
    image = Image.new("RGB", (900, 125), "#087F83")
    draw = ImageDraw.Draw(image)
    font_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    draw.text(
        (450, 62), "Configure analysis",
        font=ImageFont.truetype(font_path, 52),
        fill="#FFFFFF", anchor="mm"
    )
    return image


def show_settings_section(section):
    return tuple(gr.update(visible=(section == name))
                 for name in ["Data", "Risk", "Display"])


# Build this panel inside the parent dashboard's Blocks app
# Pass that app as the app argument so initial events belong to it
def build_distribution_panel(app):
    defaults = [name for name in [
        "Technology", "Financials", "Healthcare", "Energy"
    ] if name in df.columns]
    if not defaults:
        defaults = list(df.columns[:4])

    # A single navy header keeps title and selection details together.
    active_selection = gr.Image(
        value=selection_summary(
            defaults, "Monthly", df.index.min().strftime("%d/%m/%Y"),
            df.index.max().strftime("%d/%m/%Y")
        ),
        label="Return distributions",
        alt_text="Return distributions. Sector return patterns and historical tail risk.",
        show_label=False, container=False, interactive=False,
        buttons=[], width="100%", format="png"
    )

    with gr.Row(equal_height=False):
        # PANEL 1: a compact settings sidebar
        with gr.Column(scale=1, min_width=270):
            with gr.Group():
                gr.Image(
                    value=make_controls_banner(), label="Configure analysis",
                    alt_text="Configure analysis", show_label=False,
                    container=False, interactive=False, buttons=[],
                    width="100%", format="png"
                )
                # Centre the navigation group using native layout components.
                with gr.Row():
                    gr.Markdown("", scale=1, min_width=0)
                    settings_navigation = gr.Radio(
                        choices=["Data", "Risk", "Display"], value="Data",
                        label="Settings section", show_label=False,
                        container=False, scale=0, min_width=235
                    )
                    gr.Markdown("", scale=1, min_width=0)
                with gr.Column(visible=True) as data_section:
                    chart_input = gr.Dropdown(
                        choices=["Histogram", "Box plot", "Violin plot",
                                 "Cumulative probability", "Normal Q-Q"],
                        value="Histogram", label="Analysis", container=True,
                        filterable=False
                    )
                    frequency_input = gr.Radio(
                        choices=["Daily", "Monthly"], value="Monthly",
                        label="Return frequency", container=True
                    )
                    with gr.Accordion(
                        f"Sectors · {len(defaults)} selected", open=False
                    ) as sector_picker:
                        sector_input = gr.CheckboxGroup(
                            choices=list(df.columns), value=defaults,
                            label="Included sectors", container=True
                        )
                    with gr.Row():
                        start_input = gr.Textbox(
                            value=df.index.min().strftime("%d/%m/%Y"),
                            label="From", placeholder="DD/MM/YYYY",
                            lines=1, max_lines=1, min_width=0,
                            scale=1, container=True
                        )
                        end_input = gr.Textbox(
                            value=df.index.max().strftime("%d/%m/%Y"),
                            label="To", placeholder="DD/MM/YYYY",
                            lines=1, max_lines=1, min_width=0,
                            scale=1, container=True
                        )
                with gr.Column(visible=False) as risk_section:
                    with gr.Column() as downside_settings:
                        gr.Markdown("**Historical downside overlays**")
                        loss_line_input = gr.Checkbox(
                            value=True, label="Show loss threshold", container=True
                        )
                        loss_input = gr.Number(
                            value=-4, minimum=-30, maximum=0, step=0.5,
                            label="Loss threshold (%)", container=True
                        )
                        tail_input = gr.Checkbox(
                            value=False, label="Show historical tail", container=True
                        )
                        confidence_input = gr.Slider(
                            minimum=90, maximum=99, value=95, step=1,
                            label="Tail confidence (%)", container=True
                        )
                        gr.Markdown(
                            "95% confidence selects the lowest 5% of historical returns."
                        )
                with gr.Column(visible=False) as display_section:
                    with gr.Column() as histogram_settings:
                        range_input = gr.Radio(
                            choices=["Central 98%", "Full range"],
                            value="Central 98%", label="Histogram window",
                            container=True
                        )
                        bins_input = gr.Slider(
                            minimum=10, maximum=100, value=50, step=5,
                            label="Histogram bins", container=True
                        )
                        curve_input = gr.Checkbox(
                            value=True, label="Density curve", container=True
                        )
                        normal_input = gr.Checkbox(
                            value=False, label="Normal reference", container=True
                        )
                    gr.Markdown("Shape settings apply to histograms.")

        # PANEL 2: the chart gets the full remaining width
        with gr.Column(scale=5, min_width=0):
            with gr.Group():
                chart_heading = gr.Markdown("### Histogram")
                validation_message = gr.Markdown()
                graph = gr.Plot(show_label=False, container=False)

                # This section exists only for histogram range information
                with gr.Accordion(
                    "Histogram window · range and excluded-from-view counts",
                    open=False, visible=True
                ) as range_details:
                    message = gr.Markdown()

    # Findings use the current sample, rather than generic fixed claims.
    with gr.Group():
        gr.Markdown("### What this sample shows")
        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=240):
                with gr.Group():
                    gr.Markdown("#### Spread")
                    spread_text = gr.Markdown()
            with gr.Column(scale=1, min_width=240):
                with gr.Group():
                    gr.Markdown("#### Downside")
                    downside_text = gr.Markdown()
            with gr.Column(scale=1, min_width=240):
                with gr.Group():
                    gr.Markdown("#### Loss frequency")
                    loss_text = gr.Markdown()
        with gr.Accordion("Sample and calculation notes", open=False):
            findings_text = gr.Markdown()
        with gr.Accordion("Compare exact values", open=False):
            gr.Markdown(
                "All returns are percentages; the middle-50% range is in "
                "percentage points (pp). Tail measures use the confidence "
                "selected in Risk. Values are rounded to three decimal places."
            )
            comparison_table = gr.Dataframe(
                value=pd.DataFrame(columns=[
                    "Sector", "Median return (%)", "Middle-50% range (pp)",
                    "Tail cutoff (%)", "Tail mean (%)"
                ]),
                interactive=False, label="Selected-period comparison",
                show_label=False
            )

    # Reading material sits below the chart instead of squeezing it
    with gr.Group():
        with gr.Tabs():
            with gr.Tab("Interpretation"):
                chart_hint = gr.Markdown(chart_explanation("Histogram"))
                chart_notes = gr.Markdown(reading_notes("Histogram"))
            with gr.Tab("Reference lines"):
                gr.Markdown(
                    "**Dashed red:** the selected loss threshold (default −4%).\n\n"
                    "**Histogram dotted line / box and violin diamonds:** "
                    "the historical lower-tail cutoff.\n\n"
                    "**Box and violin crosses:** average return at or below "
                    "that cutoff, called the tail mean.\n\n"
                    "Q-Q uses a normal reference line instead of downside overlays."
                )
            with gr.Tab("Methodology"):
                gr.Markdown(
                    "Monthly returns compound daily decimal returns. Only "
                    "whole calendar months inside the selection are included. "
                    "Months containing missing daily observations are excluded. "
                    "Selected sectors use common complete observations."
                )
                gr.Markdown(
                    "The central histogram window changes the view, not the "
                    "sample used for density or tail calculations. Full range "
                    "displays the extremes. These are historical estimates, "
                    "not forecasts."
                )

    settings_navigation.change(
        fn=show_settings_section, inputs=settings_navigation,
        outputs=[data_section, risk_section, display_section], queue=False
    )

    #Keep this order identical to the function's parameters
    inputs = [sector_input, start_input, end_input, bins_input,
              frequency_input, loss_input, curve_input, normal_input,
              tail_input, confidence_input, chart_input, range_input, loss_line_input]
    outputs = [graph, validation_message, message, spread_text, downside_text,
               loss_text, findings_text, comparison_table]
    app.load(fn=render_distribution, inputs=inputs, outputs=outputs,
             concurrency_id="distribution", concurrency_limit=1)
    for control in inputs:
        control.change(
            fn=render_distribution, inputs=inputs, outputs=outputs,
            trigger_mode="always_last", concurrency_id="distribution",
            concurrency_limit=1
        )
    sector_input.change(
        fn=lambda selected: gr.update(
            label=f"Sectors · {len(selected or [])} selected"
        ), inputs=sector_input, outputs=sector_picker, queue=False
    )
    chart_input.change(
        fn=update_controls, inputs=chart_input,
        outputs=[histogram_settings, downside_settings, chart_hint,
                 range_details, chart_notes, chart_heading], queue=False
    )
    for control in [sector_input, frequency_input, start_input, end_input]:
        control.change(
            fn=selection_summary,
            inputs=[sector_input, frequency_input, start_input, end_input],
            outputs=active_selection, queue=False
        )
    return {"graph": graph, "message": message, "inputs": inputs,
            "range_details": range_details, "error": validation_message,
            "findings": findings_text, "comparison_table": comparison_table}


# Share this theme with the parent dashboard if required
def make_distribution_theme():
    # Use only native Gradio theme settings; no CSS or HTML layout.
    return gr.themes.Base(
        primary_hue="teal", secondary_hue="slate", neutral_hue="slate",
        spacing_size="sm", radius_size="sm", text_size="sm",
        font=["Arial", "sans-serif"]
    ).set(
        body_background_fill="#EFF2F6",
        body_background_fill_dark="#EFF2F6",
        background_fill_primary="#FFFFFF",
        background_fill_primary_dark="#FFFFFF",
        background_fill_secondary="#F5F7FA",
        background_fill_secondary_dark="#F5F7FA",
        block_background_fill="#FFFFFF",
        block_background_fill_dark="#FFFFFF",
        block_border_width="0px",
        block_border_color="#E3E8EF",
        block_border_color_dark="#E3E8EF",
        block_shadow="none",
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


# Start the app only when this file is run directly
if __name__ == "__main__":
    with gr.Blocks(title="Return distributions", fill_width=True) as demo:
        build_distribution_panel(demo)
    demo.launch(inbrowser=True, theme=make_distribution_theme())
