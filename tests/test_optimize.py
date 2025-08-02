import os
import numpy as np
from pathlib import Path
import pandas as pd
from pyromof import optimize

TEST_PATH = Path(__file__).parent
ROOT_PATH = TEST_PATH.parent

def test_minimalexample():
    '''
    Runs the entire optimize.py with the minimal example and
    checks whether errors occur.
    '''
    profiles, sinks, sources, converters, storage, general = optimize.read_raw_data(
        os.path.join(TEST_PATH, "files", "input_data.xlsx")
    )
    SCENARIO_PATH, META_INFO, DUMPING_SPACE = optimize.define_and_create_folders(Path(__file__).parent.parent, "minimalexample")
    time = pd.date_range(
        start="2023-01-02 02:00", end="2023-01-02 05:00", freq="h", inclusive="both"
    )
    es, om, investment, epcs = optimize.create_energysystem(
        META_INFO=META_INFO, 
        profiles=profiles, 
        sinks=sinks, 
        sources=sources, 
        converters=converters, 
        storage=storage, 
        general=general, 
        time=time, 
        scenario="minimalexample"
    )
    # (not finished)