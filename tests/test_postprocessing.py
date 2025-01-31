import sys
import os
import numpy as np
from pathlib import Path
import pandas as pd

TEST_PATH = Path(__file__).parent
ROOT_PATH = TEST_PATH.parent
sys.path.append(ROOT_PATH)
from pyromof import postprocessing


def test_calculate_variable_costs_per_flow_per_timestep():
    path_sequences = os.path.join(TEST_PATH, "files", "sequences.csv")
    path_varcosts = os.path.join(TEST_PATH, "files", "variable_costs_from_model.csv")
    effective_variable_costs = (
        postprocessing.calculate_variable_costs_per_flow_per_timestep(
            path_sequences, path_varcosts
        )
    )
    expected_result = pd.DataFrame(
        columns=[
            "('b_biochar to biochar_market')",
            "('b_electricity_2 to electricity_grid')",
            "('b_co2 to co2_market')",
        ],
        index=[
            "2023-01-02 00:00:00",
            "2023-01-02 01:00:00",
            "2023-01-02 02:00:00",
            "2023-01-02 03:00:00",
        ],
        data={
            "('b_biochar to biochar_market')": [0, 0, 0, np.nan],
            "('b_electricity_2 to electricity_grid')": [-0.2, -0.2, -0.2, np.nan],
            "('b_co2 to co2_market')": [0.02, 0.02, 0.02, np.nan],
        },
    )
    assert effective_variable_costs.equals(expected_result)
