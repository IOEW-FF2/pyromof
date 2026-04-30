from pathlib import Path
from pyromof import (
    load_demand_profiles,
    optimize,
    postprocessing,
    plotting,
    load_duration_curve,
    compare_scenarios,
    analyse_sensitivity,
    measure_flexibility,
)

pyromof = Path(__file__).parent

PIPELINE_STEPS = {
    "load_demand_profiles": load_demand_profiles.load_demand_profiles,
    "optimize": optimize.optimize,
    "postprocess": postprocessing.postprocess,
    "plot_sequences_and_scalars": plotting.plot_sequences_and_scalars,
    "plot_load_duration_curves": load_duration_curve.plot_load_duration_curves,
    "compare_scenarios": compare_scenarios.compare_scenarios,
    "measure_flexibility": measure_flexibility.measure_flexibility,
    "analyse_sensitivity": analyse_sensitivity.analyze_sensitivity,
}


def run_pipeline(steps, scenario=None):
    for step in steps:
        if step in PIPELINE_STEPS:
            print(f"Running {step}...")
            if step == "plot_load_duration_curves" and scenario:
                PIPELINE_STEPS[step](scenario)
            else:
                PIPELINE_STEPS[step]()
        else:
            print(f"Step {step} is not recognized. Skipping.")
