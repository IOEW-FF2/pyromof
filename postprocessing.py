import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import logging
logging.basicConfig(filename='logging.log', format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', encoding='utf-8', level=logging.INFO)

from oemof.solph import EnergySystem, Model, processing, components, buses, flows, create_time_index, views

# scenario definition
ROOT_PATH = Path(__file__).parent

es = EnergySystem()
es.restore(ROOT_PATH , 'es_dump.oemof')

logging.info('The EnergySystem is restored.')
# now we use the write results method to write the scalar results in oemof-tabular
# format

flows = [x for x in es.results.keys() if x[1] is not None]
nodes = [x for x in es.results.keys() if x[1] is None] # This is only storage

# Simple manual workaround to assess flow-data: Search in list(es.results.keys()) for the desired key
# and then print the sequence as a dataframe: list(es.results.values())[10]["sequences"]

# plots and result processing

# These are dictionaries with "sequences" as key and the relevant sequences for each node in a dataframe:
results_pyrolysis_energy = views.node(es.results, 'conversion_orc')
results_pyrolysis_energy["sequences"].to_csv(str(ROOT_PATH / "results_pyrolysis_energy.csv"))
results_pyrolysis_material = views.node(es.results, 'conversion_bc')
results_pyrolysis = views.node(es.results, 'pyrolysis')

def plot_figures_for(element: dict, filename):
    figure, axes = plt.subplots(figsize=(10, 5))
    element["sequences"].plot(ax=axes, kind="line", drawstyle="steps-post")
    plt.legend(
        loc="upper center",
        prop={"size": 8},
        bbox_to_anchor=(0.5, 1.25),
        ncol=2,
    )
    #axes.legend(labels=['biomass input', 'electricity input', 'biochar output', 'syngas output'])
    axes.set_ylabel('kWh')
    figure.subplots_adjust(top=0.8)
    figure.savefig(str(ROOT_PATH / filename))

# plot_figures_for(results_pyrolyse)
# plot_figures_for(results_pyrolyse_materiell)
plot_figures_for(results_pyrolysis, "results_pyrolysis.jpg")