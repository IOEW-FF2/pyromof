import sys
import os
from pathlib import Path
import pandas as pd

ROOT_PATH = Path(__file__).parent.parent
sys.path.append(ROOT_PATH)
from pyromof import postprocessing
# This executes all code in postprocessing, which doesn't work on github because there's not dumping space.


def test_list_int():
    """
    Test that it can sum a list of integers
    """
    assert sum((1, 2, 3)) == 6

def test_calculate_variable_costs_per_flow_per_timestep():
    path_sequences = os.path.join("files", "sequences.csv")
    path_varcosts = os.path.join("files", "variable_costs_from_model.csv")
    effective_variable_costs = postprocessing.calculate_variable_costs_per_flow_per_timestep(path_sequences, path_varcosts)
    expected_result = pd.DataFrame()