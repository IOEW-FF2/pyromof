import pandas as pd
import os
from pathlib import Path

def calculate_electricity_fed_in_at_negative_price_timesteps(sequences, profiles):
    """
    This function identifies the timesteps where electricity is fed into the grid at a negative price and sums up the amount of electricity fed in at these timesteps.
    """
    # Align indices: keep only timestamps that exist in both dataframes
    common_index = sequences.index.intersection(profiles.index)
    sequences_aligned = sequences.loc[common_index]
    profiles_aligned = profiles.loc[common_index]
    
    # Identify the timesteps with negative electricity prices
    negative_price_timesteps = profiles_aligned[profiles_aligned["profile_electricity_remuneration"] > 0].index

    # Sum up the electricity fed into the grid at these timestepsSS
    fed_in_at_negative_price = sequences_aligned.loc[negative_price_timesteps, sequences_aligned.columns.str.contains("b_electricity to electricity_grid")].sum().sum()

    share_of_total_electricity_fed_in = fed_in_at_negative_price / sequences_aligned["b_electricity to electricity_grid"].sum().sum()
    print(fed_in_at_negative_price)
    print(share_of_total_electricity_fed_in*100)
    return fed_in_at_negative_price

def calculate_pyrolysis_full_load_hours(sequences):
    """
    This function calculates the full load hours of the pyrolysis process based on the amount of biochar produced.
    """
    total_biochar_produced = sequences["b_biochar to biochar_market"].sum()
    pyrolysis_capacity = sequences["b_biochar to biochar_market"].max()
    full_load_hours = total_biochar_produced / pyrolysis_capacity
    print("full load hours: " + str(full_load_hours))
    return full_load_hours

if __name__ == "__main__":
    general = pd.read_excel("input_data.xlsx", sheet_name="general")
    scenario = "stromflex_h2_0"

    ROOT_PATH = Path(__file__).parent.parent
    SCENARIO_RESULTS = os.path.join(ROOT_PATH, "results", scenario, "results")
    SCENARIO_META_INFO = os.path.join(ROOT_PATH, "results", scenario, "meta_info")

sequences = pd.read_csv(os.path.join(SCENARIO_RESULTS, "sequences.csv"), sep=";", index_col=0)
profiles = pd.read_excel(os.path.join(SCENARIO_META_INFO, "input_data.xlsx"), sheet_name="profiles", index_col=0)
calculate_electricity_fed_in_at_negative_price_timesteps(sequences, profiles)
calculate_pyrolysis_full_load_hours(sequences)