import matplotlib.pyplot as plt
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

    plot_figures_for(results_pyrolysis_energy, "pyrolysis_outputs_energy.png")
    plot_figures_for(results_pyrolysis, "pyrolysis.png")
    plot_figures_for(results_heat_demand, "results_heat_demand.png")
