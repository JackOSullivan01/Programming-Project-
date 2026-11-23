from pathlib import Path
from scipy import stats

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


# Gradio runs this function whenever an input changes
def draw_histogram(
        sector, start_date, end_date, bins, frequency, loss_threshold,
        show_curve, show_normal, show_tail, confidence
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
            color="#2563EB",
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

    plt.close(fig)

    # Return the graph and clear any previous message
    return fig, ""


# Create the webpage
with gr.Blocks(title="Return distributions") as demo:

    gr.Markdown("# Return distributions")

    with gr.Row():
        sector_input = gr.Dropdown(
            choices=list(df.columns),
            value=[df.columns[0]],
            multiselect=True,
            label="Sector"
        )

        start_input = gr.Textbox(
            value=df.index.min().strftime("%Y-%m-%d"),
            label="Start date · YYYY-MM-DD"
        )

        end_input = gr.Textbox(
            value=df.index.max().strftime("%Y-%m-%d"),
            label="End date · YYYY-MM-DD"
        )

        bins_input = gr.Slider(
            minimum=10,
            maximum=100,
            value=30,
            step=5,
            label="Number of bins"
        )

        frequency_input = gr.Dropdown(
            choices=["Daily", "Monthly"],
            value="Daily",
            label="Return frequency"
        )

        loss_input = gr.Slider(
            minimum=-30,
            maximum=0,
            value=-5,
            step=0.5,
            label="Loss threshold (%)"
        )

        #Let the user show or hide the density curves
        curve_input = gr.Checkbox(
            value=True,
            label="Show density curve"
        )

        #Let the user compare returns with a fitted normal distribution
        normal_input = gr.Checkbox(
            value=False,
            label="Show normal reference"
        )

    #Let the user show or hide the downside-tail analysis
    tail_input = gr.Checkbox(
        value=True,
        label="Show downside tail"
    )

    #Choose how much of the lower tail to highlight
    confidence_input = gr.Slider(
        minimum=90,
        maximum=99,
        value=95,
        step=1,
        label="Tail confidence (%)"
    )

    graph = gr.Plot(show_label=False)
    message = gr.Markdown()

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
        confidence_input
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
    demo.launch(inbrowser=True)