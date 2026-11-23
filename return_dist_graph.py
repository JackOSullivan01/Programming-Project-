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
def draw_histogram(sector, start_date, end_date, bins):

    # Convert the user's text inputs into dates
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")

    if pd.isna(start) or pd.isna(end):
        return None, "Enter dates as YYYY-MM-DD."

    if start > end:
        return None, "Choose a start date before the end date."

    # Filter the dates and select the chosen sector
    selected_data = df.loc[start:end]

    # Convert decimal returns to percentages
    sector_returns = selected_data[sector].dropna() * 100

    if sector_returns.empty:
        return None, "There are no trading observations in this period."

    # Create the histogram
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.hist(
        sector_returns,
        bins=int(bins),
        color="#2563EB",
        edgecolor="white"
    )

    ax.set_title(f"{sector}: daily returns")
    ax.set_xlabel("Daily return (%)")
    ax.set_ylabel("Number of trading days")

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

    graph = gr.Plot(show_label=False)
    message = gr.Markdown()

    inputs = [sector_input, start_input, end_input, bins_input]
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