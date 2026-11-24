from pathlib import Path
from scipy import stats
from matplotlib.ticker import PercentFormatter

import gradio as gr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


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


# Gradio runs this function whenever an input changes
def draw_histogram(
        sector, start_date, end_date, bins, frequency, loss_threshold,
        show_curve, show_normal, show_tail, confidence, chart_type,
        view_range="Central 98%", show_loss=False
):

    if not sector:
        return None, "Choose at least one sector."

    # Convert the text inputs into dates
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")

    # Check the dates are valid
    if pd.isna(start) or pd.isna(end):
        return None, "Enter dates as YYYY-MM-DD."

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

    if chart_type == "Normal Q-Q":

        #Keep sectors with enough observations for comparison
        available_sectors = []

        for selected_sector in sector:
            if sector_returns[selected_sector].count() >= 3:
                available_sectors.append(selected_sector)

        if not available_sectors:
            return None, "Choose a period with at least three observations."

        #Create a separate panel for each selected sector
        number_of_sectors = len(available_sectors)
        columns = 1 if number_of_sectors == 1 else 2
        rows = (number_of_sectors + columns - 1) // columns

        fig, axes = plt.subplots(
            rows,
            columns,
            figsize=(11.5, 2.2 * rows + 0.6),
            dpi=180,
            sharex=True,
            sharey=True,
            squeeze=False,
            layout="constrained"
        )

        for i, selected_sector in enumerate(available_sectors):
            ax = axes.flat[i]
            values = sector_returns[selected_sector].dropna()

            #Calculate theoretical normal quantiles and observed quantiles
            quantiles, fitted_line = stats.probplot(
                values,
                dist="norm"
            )

            theoretical, observed = quantiles
            slope, intercept, correlation = fitted_line

            #Plot the observed returns against theoretical quantiles
            ax.scatter(
                theoretical,
                observed,
                color=PALETTE[selected_sector],
                s=12,
                alpha=0.65,
                linewidths=0
            )

            #Draw the fitted normal reference line
            ax.plot(
                theoretical,
                slope * theoretical + intercept,
                color="#17283E",
                linestyle="--",
                linewidth=1.5,
                label="Normal reference"
            )

            ax.set_title(selected_sector)
            ax.set_xlabel("Theoretical normal quantile")
            ax.set_ylabel(f"{frequency} return (%)")
            ax.legend(frameon=False, fontsize=8)

        #Hide unused panels
        for i in range(number_of_sectors, rows * columns):
            axes.flat[i].set_visible(False)

        style_figure(fig)
        add_graph_details(fig, sector_returns, frequency)
        plt.close(fig)

        return fig, ""
 
    #Draw the cumulative probability of returns for each sector
    if chart_type == "Cumulative probability":

        fig, ax = plt.subplots(
            figsize=(11.5, 4),
            dpi=180,
            layout="constrained"
        )

        for selected_sector in sector:
            #Arrange returns from smallest to largest
            values = np.sort(
                sector_returns[selected_sector].dropna().to_numpy()
            )

            #Skip sectors with no available returns
            if len(values) == 0:
                continue

            #Calculate the cumulative proportion of observations
            probabilities = np.arange(1, len(values) + 1) / len(values)

            #Draw a step curve because these are observed probabilities
            ax.step(
                values,
                probabilities,
                where="post",
                linewidth=1.8,
                color=PALETTE[selected_sector],
                label=selected_sector
            )

        #Mark the user's chosen loss threshold
        if show_loss:
            ax.axvline(
                loss_threshold,
                color="#B84A42",
                linestyle="--",
                linewidth=1.5,
                label=f"Loss threshold: {loss_threshold}%"
            )

        #Show the selected lower-tail probability
        if show_tail:
            tail_probability = 1 - confidence / 100

            ax.axhline(
                tail_probability,
                color="#637084",
                linestyle=":",
                linewidth=1.3,
                label=f"Lower {100 - confidence:g}% probability"
            )

        #Display probabilities as percentages from 0% to 100%
        ax.set_ylim(0, 1)
        ax.yaxis.set_major_formatter(PercentFormatter(1))

        ax.set_title(
            "Cumulative probability",
            loc="left",
            fontweight="bold"
        )

        ax.set_xlabel(f"{frequency} return (%)")
        ax.set_ylabel("Proportion of observations at or below return")
        ax.legend(frameon=False, fontsize=8)

        style_figure(fig)
        add_graph_details(fig, sector_returns, frequency)
        plt.close(fig)

        return fig, ""

    #Draw box or violin plots when selected
    if chart_type in ["Box plot", "Violin plot"]:

        #Arrange the sector returns into a table for Seaborn
        records = []

        for selected_sector in sector:
            for value in sector_returns[selected_sector].dropna():
                records.append({
                    "Sector": selected_sector,
                    "Return (%)": value
                })

        plot_data = pd.DataFrame(records)

        #Give each sector a separate row for clear comparisons
        fig, ax = plt.subplots(
            figsize=(11.5, max(3.4, len(sector) * 0.43 + 0.8)),
            dpi=180,
            layout="constrained"
        )

        

        if chart_type == "Box plot":
            #Show the median, quartiles, whiskers and outliers
            sns.boxplot(
                data=plot_data,
                x="Return (%)",
                y="Sector",
                order=sector,
                hue="Sector",
                palette=PALETTE,
                dodge=False,
                legend=False,
                width=0.5,
                linewidth=1,
                fliersize=2.5,
                ax=ax
            )

        else:
            #Show the distribution shape with quartile lines inside
            sns.violinplot(
                data=plot_data,
                x="Return (%)",
                y="Sector",
                order=sector,
                hue="Sector",
                palette=PALETTE,
                dodge=False,
                legend=False,
                inner="quart",
                cut=0,
                linewidth=1,
                ax=ax
            )

        #Show a reference line for zero return
        ax.axvline(
            0,
            color="#637084",
            linewidth=0.8,
            alpha=0.6
        )

        #Mark the user's chosen loss threshold
        if show_loss:
            ax.axvline(
                loss_threshold,
                color="#B84A42",
                linestyle="--",
                linewidth=1.5,
                label=f"Loss threshold: {loss_threshold}%"
            )

        #Show the lower percentile and tail mean for each sector
        if show_tail:
            tail_probability = 1 - confidence / 100

            for i, selected_sector in enumerate(sector):
                values = sector_returns[selected_sector].dropna()

                tail_cutoff = values.quantile(tail_probability)
                tail_mean = values[values <= tail_cutoff].mean()

                #Label each marker type only once in the legend
                cutoff_label = (
                    f"Lower {100 - confidence:g}% cutoff"
                    if i == 0 else "_nolegend_"
                )

                mean_label = (
                    "Tail mean"
                    if i == 0 else "_nolegend_"
                )

                ax.scatter(
                    tail_cutoff,
                    i,
                    marker="D",
                    color="#B84A42",
                    s=35,
                    zorder=5,
                    label=cutoff_label
                )

                ax.scatter(
                    tail_mean,
                    i,
                    marker="x",
                    color="#17283E",
                    s=40,
                    zorder=5,
                    label=mean_label
                )

        #Label and display the selected graph
        ax.set_title(
            chart_type,
            loc="left",
            fontweight="bold"
        )

        ax.set_xlabel(f"{frequency} return (%)")
        ax.set_ylabel("")
        ax.legend(frameon=False, fontsize=8, loc="best")

        style_figure(fig)
        add_graph_details(fig, sector_returns, frequency)
        plt.close(fig)

        return fig, ""

    all_values = sector_returns.to_numpy().flatten()
    central = view_range == "Central 98%"
    low, high = np.quantile(all_values, [0.01, 0.99])
    if not central or low == high:
        low, high = all_values.min(), all_values.max()
    if low == high:
        low, high = low - 0.5, high + 0.5

    # Expand the central window when needed to include the chosen loss line.
    if central and show_loss:
        padding = max((high - low) * 0.025, 0.05)
        low = min(low, loss_threshold - padding)
        high = max(high, loss_threshold + padding)

    # Fine common bins within the displayed range, retaining extreme values
    # in outer bins so density remains normalised over the full sample.
    edges = np.linspace(low, high, int(bins) + 1)
    if all_values.min() < low:
        edges = np.r_[all_values.min(), edges]
    if all_values.max() > high:
        edges = np.r_[edges, all_values.max()]

    number_of_sectors = len(sector)
    columns = 1 if number_of_sectors == 1 else 2
    rows = (number_of_sectors + columns - 1) // columns

    # A wide, compact figure keeps four panels readable together
    fig, axes = plt.subplots(
        rows, columns, figsize=(11.5, 2.2 * rows + 0.6), dpi=180,
        sharex=True, sharey=True, squeeze=False, layout="constrained"
    )
    outside_messages = []
    for i, selected_sector in enumerate(sector):
        ax = axes.flat[i]
        values = sector_returns[selected_sector].dropna()
        ax.hist(
            values, bins=edges, density=True,
            color=PALETTE[selected_sector], edgecolor="white", linewidth=0.45
        )

        # Estimate density from the full sample, even in the central view
        if show_curve and len(values) >= 3 and values.nunique() > 1:
            x_values = np.linspace(low, high, 500)
            ax.plot(
                x_values, stats.gaussian_kde(values)(x_values),
                color="#17345C", linewidth=1.7, label="Density curve"
            )
        if show_normal and len(values) >= 3 and values.std() > 0:
            x_values = np.linspace(low, high, 500)
            ax.plot(
                x_values,
                stats.norm.pdf(x_values, loc=values.mean(), scale=values.std()),
                color="#637084", linestyle="--", linewidth=1.4,
                label="Normal reference"
            )

        # Tail calculations always use every selected observation
        if show_tail:
            tail_cutoff = values.quantile(1 - confidence / 100)
            tail_mean = values[values <= tail_cutoff].mean()
            if tail_cutoff > low:
                ax.axvspan(low, min(high, tail_cutoff), color="#B84A42", alpha=0.10)
            ax.axvline(
                tail_cutoff, color="#B84A42", linestyle=":", linewidth=1.5,
                label=f"Lower {100 - confidence:g}% cutoff"
            )
            ax.text(
                0.98, 0.96,
                f"Cutoff {tail_cutoff:.2f}%\nTail mean {tail_mean:.2f}%",
                transform=ax.transAxes, ha="right", va="top", fontsize=7,
                color="#B84A42",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85}
            )
        if show_loss:
            ax.axvline(
                loss_threshold, color="#DC2626", linestyle="--", linewidth=1.2,
                label=f"Loss threshold {loss_threshold:g}%"
            )

        ax.set_xlim(low, high)
        ax.set_title(selected_sector, loc="left", fontsize=10)
        ax.tick_params(labelbottom=True)
        if i // columns == rows - 1:
            ax.set_xlabel(f"{frequency} return (%)", fontsize=8)
        if i % columns == 0:
            ax.set_ylabel("Density", fontsize=8)

        if central:
            outside = int(((values < low) | (values > high)).sum())
            outside_messages.append(
                f"{selected_sector}: {outside:,} ({outside / len(values):.1%})"
            )

    for i in range(number_of_sectors, rows * columns):
        axes.flat[i].set_visible(False)

    # One shared legend replaces the repeated panel legends
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles, labels, loc="outside lower center",
            ncol=min(4, len(handles)), frameon=False, fontsize=8
        )
    style_figure(fig)
    add_graph_details(fig, sector_returns, frequency)
    plt.close(fig)

    message = ""
    if central:
        message = (
            f"**Central 98% view:** shared limits {low:.2f}% to {high:.2f}% "
            "start from the pooled first and 99th percentiles and expand if needed "
            "to include the selected loss line. Observations outside "
            "the view: " + "; ".join(outside_messages) +
            ". No observations are removed from density or tail calculations. "
            "Choose Full range to see the extremes."
        )
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


# Generate a simple fixed preview for the dashboard overview
def make_distribution_preview():
    selected = [name for name in [
        "Technology", "Financials", "Healthcare", "Energy"
    ] if name in df.columns]
    if not selected:
        selected = list(df.columns[:4])

    monthly = (1 + df[selected]).resample("ME").prod(min_count=1) - 1
    missing = df[selected].isna().resample("ME").sum()
    monthly = monthly.mask(missing > 0).dropna() * 100

    fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
    plotted = False
    for selected_sector in selected:
        values = monthly[selected_sector].dropna()
        if len(values) >= 3 and values.nunique() > 1:
            sns.kdeplot(
                x=values, color=PALETTE.get(selected_sector, "#17283E"),
                linewidth=2, cut=0, label=selected_sector, ax=ax
            )
            plotted = True
    if not plotted:
        ax.text(0.5, 0.5, "Not enough monthly data for a preview.",
                transform=ax.transAxes, ha="center")
    else:
        ax.legend(frameon=False)
    ax.set_xlabel("Monthly return (%)")
    ax.set_ylabel("Density")
    style_figure(fig)
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
    if inputs[12] and inputs[5] is None:
        return None, "Enter a loss threshold, or turn its reference line off.", ""
    fig, text = draw_histogram(*inputs)
    if fig is None:
        return None, text, ""
    return fig, "", text


def selection_summary(sectors, frequency, start_date, end_date):
    return (
        f"**{len(sectors or [])} sectors** · **{frequency} returns**  \n"
        f"{start_date} — {end_date}"
    )


# Build this panel inside the parent dashboard's Blocks app
# Pass that app as the app argument so initial events belong to it
def build_distribution_panel(app):
    defaults = [name for name in [
        "Technology", "Financials", "Healthcare", "Energy"
    ] if name in df.columns]
    if not defaults:
        defaults = list(df.columns[:4])

    # A restrained editorial heading, rather than competing slogans
    with gr.Row(equal_height=False):
        with gr.Column(scale=3, min_width=0):
            gr.Markdown("# Return distributions")
            gr.Markdown("**A clearer view of sector returns, from typical outcomes to tail risk.**")
        with gr.Column(scale=1, min_width=220):
            active_selection = gr.Markdown(selection_summary(
                defaults, "Monthly", df.index.min().strftime("%Y-%m-%d"),
                df.index.max().strftime("%Y-%m-%d")
            ))

    with gr.Row(equal_height=False):
        # PANEL 1: a compact settings sidebar
        with gr.Column(scale=1, min_width=270):
            with gr.Group():
                gr.Markdown("### Configure analysis")
                with gr.Tabs():
                    with gr.Tab("Data"):
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
                                value=df.index.min().strftime("%Y-%m-%d"),
                                label="From", placeholder="YYYY-MM-DD",
                                lines=1, max_lines=1, min_width=0,
                                scale=1, container=True
                            )
                            end_input = gr.Textbox(
                                value=df.index.max().strftime("%Y-%m-%d"),
                                label="To", placeholder="YYYY-MM-DD",
                                lines=1, max_lines=1, min_width=0,
                                scale=1, container=True
                            )
                    with gr.Tab("Risk"):
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
                    with gr.Tab("Display"):
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
            gr.Markdown("Changes update the chart automatically.")

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

    #Keep this order identical to the function's parameters
    inputs = [sector_input, start_input, end_input, bins_input,
              frequency_input, loss_input, curve_input, normal_input,
              tail_input, confidence_input, chart_input, range_input, loss_line_input]
    outputs = [graph, validation_message, message]
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
            "range_details": range_details, "error": validation_message}


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
