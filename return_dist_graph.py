from pathlib import Path

import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt


# Load the cleaned dataset
filename = Path(__file__).parent / "industry_returns_clean.csv"

df = pd.read_csv(
    filename,
    parse_dates=["Date"],
    index_col="Date"
).sort_index()


# Gradio runs this function whenever an input changes
def draw_histogram(
        sector, start_date, end_date, bins, frequency, loss_threshold
):

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

    # Create the histogram
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.hist(
        sector_returns,
        bins=int(bins),
        color="#2563EB",
        edgecolor="white"
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

    ax.set_title(f"{sector}: {frequency.lower()} returns")
    ax.set_xlabel(f"{frequency} return (%)")
    ax.set_ylabel("Number of observations")

    plt.close(fig)

    # Return the graph and clear any previous message
    return fig, ""


# Create the webpage
with gr.Blocks(title="Return distributions") as demo:

    gr.Markdown("# Return distributions")

    with gr.Row():
        sector_input = gr.Dropdown(
            choices=list(df.columns),
            value=df.columns[0],
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

    graph = gr.Plot(show_label=False)
    message = gr.Markdown()

    inputs = [
        sector_input,
        start_input,
        end_input,
        bins_input,
        frequency_input,
        loss_input
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