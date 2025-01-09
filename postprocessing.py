import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import logging
logging.basicConfig(filename=os.path.join('meta_info','logging.log'), format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', encoding='utf-8', level=logging.INFO)

from oemof.solph import EnergySystem, Model, processing, components, buses, flows, create_time_index, views

# scenario definition
ROOT_PATH = Path(__file__).parent
RESULTS = os.path.join(ROOT_PATH, 'results')

es = EnergySystem()
es.restore(ROOT_PATH , 'es_dump.oemof')

logging.info('The EnergySystem is restored.')

# Meta-information could be assessed in es.results["meta"] to retreive the objective variable.

es.results = es.results["main"]

flows = [x for x in es.results.keys() if x[1] is not None]
nodes = [x for x in es.results.keys() if x[1] is None] # This is only storage

# Simple manual workaround to assess flow-data: Search in list(es.results.keys()) for the desired key
# and then print the sequence as a dataframe: list(es.results.values())[10]["sequences"]

# plots and result processing

# These are dictionaries with "sequences" as key and the relevant sequences for each node in a dataframe:
results_pyrolysis_energy = views.node(es.results, 'conversion_orc')
results_pyrolysis_material = views.node(es.results, 'conversion_bc')
results_pyrolysis = views.node(es.results, 'pyrolysis')
results_heat_demand = views.node(es.results, 'heat_demand')

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
    # # Would be nice to shorten the labels, but it's not always the first element that is relevant. This depends on whether the bus is an in- or outflow.
    labels = [element["sequences"].columns[i][0] for i in range(len(element["sequences"].columns))]
    axes.legend(labels=labels)
    axes.set_ylabel('kWh')
    figure.subplots_adjust(top=0.8)
    figure.savefig(os.path.join(RESULTS, filename))
    element["sequences"].to_csv(os.path.join(RESULTS, filename + ".csv"))

plot_figures_for(results_pyrolysis_energy, "pyrolysis_outputs_energy.png")
plot_figures_for(results_pyrolysis_material, "pyrolysis_outputs_material.png")
plot_figures_for(results_pyrolysis, "pyrolysis.png")
plot_figures_for(results_heat_demand, "results_heat_demand.png")