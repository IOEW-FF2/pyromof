import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
import helpers
from pathlib import Path
from oemof.solph import EnergySystem, views

ROOT_PATH = Path(__file__).parent.parent
RESULTS = os.path.join(ROOT_PATH, "results")
DUMPING_SPACE = os.path.join(ROOT_PATH, "dumping_space")


def plot_figures_for(element: dict, filename):
    figure, axes = plt.subplots(figsize=(10, 5))
    element["sequences"].plot(ax=axes, kind="line", drawstyle="steps-post")
    plt.legend(
        loc="upper center",
        prop={"size": 8},
        bbox_to_anchor=(0.5, 1.25),
        ncol=2,
    )
    # labels = [element["sequences"].columns[i][0][0] for i in range(len(element["sequences"].columns))]
    # # Would be nice to shorten the labels, but it's not always the first element that is relevant.
    # This depends on whether the bus is an in- or outflow.
    labels = [
        element["sequences"].columns[i][0]
        for i in range(len(element["sequences"].columns))
    ]
    axes.legend(labels=labels)
    axes.set_ylabel("kWh")
    figure.subplots_adjust(top=0.8)
    figure.savefig(os.path.join(RESULTS, filename))
    element["sequences"].to_csv(os.path.join(RESULTS, filename + ".csv"))


def prepare_cost_sequences_for_plotting():
    """
    Reads the csv files of time-variable cost data, selects the columns that contain non-0 data and stores them in
    a dictionary of dataframes, sorted by the cost type (e.g. variable costs, start-up costs)
    """
    # Create a dictionary to hold the dataframes:
    df_dict = {}
    varcosts = pd.read_csv(
        os.path.join(RESULTS, "effective_variable_costs.csv"),
        sep=";",
        index_col=0,
        parse_dates=True,
    )
    # Remove all columns where all values are 0
    varcosts = varcosts.loc[:, varcosts.any()]
    varcosts = varcosts * -1
    df_dict["variable costs"] = varcosts
    # When more types of variable costs occur, the code for converting them in dfs ready for plotting should be added here:
    return df_dict


def plot_cost_sequences(df_dict):
    """
    Takes a dictionary of dataframes and plots them, each with a different line style.
    """
    dashtypes = [
        "solid",
        "dot",
        "dash",
        "longdash",
        "dashdot",
        "longdashdot",
    ]  # also possible: dash length list
    fig = go.Figure()
    dashtypenumber = 0
    for df in df_dict.values():
        # Loop df columns and plot columns to the figure
        for col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    mode="lines",
                    line=dict(dash=dashtypes[dashtypenumber]),  # dash='dash'
                    name=col,
                )
            )
        dashtypenumber = dashtypenumber + 1
    fig.update_layout(yaxis=dict(title="Euros/hour"))
    fig.write_html(os.path.join(RESULTS, "cost_sequences.html"))


def plot():
    df_dict = prepare_cost_sequences_for_plotting()
    plot_cost_sequences(df_dict)


if __name__ == "__main__":
    es = EnergySystem()
    es.restore(DUMPING_SPACE, "es_dump.oemof")
    scenario, investment = helpers.retreive_scenario_from_results(es)
    # These are dictionaries with "sequences" as key and the relevant sequences for each node in a dataframe:
    if investment is True:
        results_pyrolysis_energy = views.node(es.results, "conversion_orc_invest")
        results_pyrolysis = views.node(es.results, "pyrolysis_invest")
    else:
        results_pyrolysis_energy = views.node(es.results, "conversion_orc")
        results_pyrolysis = views.node(es.results, "pyrolysis")
    results_heat_demand = views.node(es.results, "heat_demand_ht")

    # plot_figures_for(results_pyrolysis_energy, "pyrolysis_outputs_energy.png")
    # plot_figures_for(results_pyrolysis, "pyrolysis.png")
    # plot_figures_for(results_heat_demand, "results_heat_demand.png")

    plot()
