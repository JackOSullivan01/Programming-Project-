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


# Gradio runs this function whenever an input changes
def draw_histogram(
        sector, start_date, end_date, bins, frequency, loss_threshold,
        show_curve, show_normal, show_tail, confidence, chart_type
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
            figsize=(10, 3 * rows),
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
        plt.close(fig)

        return fig, ""
 
    #Draw the cumulative probability of returns for each sector
    if chart_type == "Cumulative probability":

        fig, ax = plt.subplots(
            figsize=(10, 4.5),
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
            f"{frequency} cumulative return probabilities",
            loc="left",
            fontweight="bold"
        )

        ax.set_xlabel(f"{frequency} return (%)")
        ax.set_ylabel("Proportion of observations at or below return")
        ax.legend(frameon=False, fontsize=8)

        style_figure(fig)
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
            figsize=(10, max(4, len(sector) * 0.6)),
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
            f"{frequency} return distributions",
            loc="left",
            fontweight="bold"
        )

        ax.set_xlabel(f"{frequency} return (%)")
        ax.set_ylabel("")
        ax.legend(frameon=False, fontsize=8, loc="best")

        style_figure(fig)
        plt.close(fig)

        return fig, ""

    all_values = sector_returns.to_numpy().flatten()

    edges = np.histogram_bin_edges(
        all_values,
        bins=int(bins)
    )

    number_of_sectors = len(sector)
    columns = 1 if number_of_sectors == 1 else 2
    rows = (number_of_sectors + columns - 1) // columns

    #Creates the histogram
    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(8, 3 * rows),
        sharex=True,
        sharey=True,
        squeeze=False,
        layout="constrained"
    )

    for i, selected_sector in enumerate(sector):
        ax = axes.flat[i]

        ax.hist(
            sector_returns[selected_sector],
            bins=edges,
            density=True,
            color=PALETTE[selected_sector],
            edgecolor="white"
        )

        values = sector_returns[selected_sector].dropna()

        #Draw the curve if selected and enough different values exist
        if show_curve and len(values) >= 3 and values.nunique() > 1:
            sns.kdeplot(
                x=values,
                color="#17345C",
                linewidth=2,
                cut=0,
                label="Density curve",
                ax=ax
            )

         #Calculate the sector's average return and standard deviation
        mean_return = values.mean()
        standard_deviation = values.std()

        #Draw a normal reference with the same mean and standard deviation
        if show_normal and len(values) >= 3 and standard_deviation > 0:

            #Create evenly spaced return values across the histogram
            x_values = np.linspace(edges[0], edges[-1], 300)

            # Calculate the normal probability density at each return value
            normal_density = stats.norm.pdf(
                x_values,
                loc=mean_return,
                scale=standard_deviation
            )

            #Use a dashed line to distinguish it from the density curve
            ax.plot(
                x_values,
                normal_density,
                color="#637084",
                linestyle="--",
                linewidth=1.8,
                label="Normal reference"
            )

        #Calculate the lower-tail probability from the confidence level
        tail_probability = 1 - confidence / 100

        if show_tail:
            #Find the return below which the selected proportion falls
            tail_cutoff = values.quantile(tail_probability)

            #Calculate the average return in that lower tail
            tail_mean = values[values <= tail_cutoff].mean()

            #Shade the lower-tail region
            ax.axvspan(
                edges[0],
                tail_cutoff,
                color="#B84A42",
                alpha=0.12
            )

            #Mark the estimated lower-tail percentile
            ax.axvline(
                tail_cutoff,
                color="#B84A42",
                linestyle=":",
                linewidth=1.8,
                label=f"Lower {100 - confidence:g}% cutoff"
            )

            #Display the cutoff and average tail return inside the graph
            ax.text(
                0.97,
                0.95,
                f"Cutoff: {tail_cutoff:.2f}%\n"
                f"Tail mean: {tail_mean:.2f}%",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                color="#B84A42",
                bbox={
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.85
                }
            )    

        #Mark the user's chosen loss threshold
        ax.axvline(
            loss_threshold,
            color="#DC2626",
            linestyle="--",
            linewidth=1.5,
            label=f"Loss threshold: {loss_threshold}%"
        )

        ax.legend(frameon=False)

        ax.set_title(f"{selected_sector}: {frequency.lower()} returns")
        ax.set_xlabel(f"{frequency} return (%)")
        ax.set_ylabel("Density")

    for i in range(number_of_sectors, rows * columns):
        axes.flat[i].set_visible(False)

    style_figure(fig)
    plt.close(fig)

    # Return the graph and clear any previous message
    return fig, ""


# Create the webpage
with gr.Blocks(title="Return distributions") as demo:

    gr.Markdown("## Return distributions")

    #Keep sector selection, frequency and chart choice together
    with gr.Row():
        sector_input = gr.Dropdown(
            choices=list(df.columns),
            value=[df.columns[0]],
            multiselect=True,
            label="Sectors",
            scale=3,
            min_width=180
        )

        frequency_input = gr.Dropdown(
            choices=["Daily", "Monthly"],
            value="Daily",
            label="Frequency",
            scale=1,
            min_width=100
        )

        chart_input = gr.Dropdown(
            choices=[
                "Histogram",
                "Box plot",
                "Violin plot",
                "Cumulative probability",
                "Normal Q-Q"
            ],
            value="Histogram",
            label="Analysis",
            scale=2,
            min_width=160
        )

    #Keep the dates and loss threshold in a second compact row
    with gr.Row():
        start_input = gr.Textbox(
            value=df.index.min().strftime("%Y-%m-%d"),
            label="From · YYYY-MM-DD",
            min_width=120
        )

        end_input = gr.Textbox(
            value=df.index.max().strftime("%Y-%m-%d"),
            label="To · YYYY-MM-DD",
            min_width=120
        )

        loss_input = gr.Number(
            value=-5,
            minimum=-30,
            maximum=0,
            step=0.5,
            label="Loss threshold (%)",
            min_width=100
        )

    #Hide the additional options until the user needs them
    with gr.Accordion("Analysis settings", open=False):

        with gr.Row():
            curve_input = gr.Checkbox(
                value=True,
                label="Density curve · histogram"
            )

            normal_input = gr.Checkbox(
                value=False,
                label="Normal reference · histogram"
            )

            tail_input = gr.Checkbox(
                value=True,
                label="Downside tail"
            )

        with gr.Row():
            bins_input = gr.Slider(
                minimum=10,
                maximum=100,
                value=30,
                step=5,
                label="Histogram bins"
            )

            confidence_input = gr.Slider(
                minimum=90,
                maximum=99,
                value=95,
                step=1,
                label="Tail confidence (%)"
            )

    #Display the graph without an extra component heading
    graph = gr.Plot(
        show_label=False,
        container=False
    )

    message = gr.Markdown()

    #Keep this order identical to the function's parameters
    inputs = [
        sector_input,
        start_input,
        end_input,
        bins_input,
        frequency_input,
        loss_input,
        curve_input,
        normal_input,
        tail_input,
        confidence_input,
        chart_input
    ]

    outputs = [graph, message]

    # Draw the initial graph when the page opens
    demo.load(
        fn=draw_histogram,
        inputs=inputs,
        outputs=outputs,
        concurrency_id="histogram",
        concurrency_limit=1
    )

    # Automatically update when any input changes
    for control in inputs:
        control.change(
            fn=draw_histogram,
            inputs=inputs,
            outputs=outputs,
            trigger_mode="always_last",
            concurrency_id="histogram",
            concurrency_limit=1
        )


# Start the app
if __name__ == "__main__":

    #Use compact controls and a restrained slate colourway
    theme = gr.themes.Base(
        primary_hue="slate",
        secondary_hue="teal",
        neutral_hue="slate",
        spacing_size="sm",
        radius_size="sm",
        text_size="sm"
    ).set(
        body_background_fill="#EEF1F5",
        background_fill_primary="#EEF1F5",
        background_fill_secondary="#FFFFFF",
        block_background_fill="#FFFFFF",
        block_border_color="#D4DCE5",
        body_text_color="#17283E",
        block_title_text_color="#17283E",
        input_background_fill="#F8FAFC"
    )

    demo.launch(
        inbrowser=True,
        theme=theme
    )