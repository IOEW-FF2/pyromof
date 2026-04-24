import pandas as pd
from typeguard import typechecked


def read_raw_data(relative_file_path):
    return {
        "profiles": pd.read_excel(relative_file_path, sheet_name="profiles"),
        "sinks": pd.read_excel(relative_file_path, sheet_name="sink"),
        "sources": pd.read_excel(relative_file_path, sheet_name="source"),
        "converters": pd.read_excel(relative_file_path, sheet_name="converter"),
        "storage": pd.read_excel(relative_file_path, sheet_name="storage"),
        "general": pd.read_excel(relative_file_path, sheet_name="general"),
        "policies": pd.read_excel(relative_file_path, sheet_name="policies"),
    }


@typechecked
def define_time_period(general: pd.DataFrame) -> pd.DatetimeIndex:
    # Definition of the time period
    start_time = general.loc[general["label"] == "start_time", "value"].item()
    end_time = general.loc[general["label"] == "end_time", "value"].item()
    time = pd.date_range(start=start_time, end=end_time, freq="h", inclusive="both")
    return time


def slice_time_period_from_profiles(profiles: pd.DataFrame, time: pd.DatetimeIndex) -> pd.DataFrame:
    # Slice the time period from profiles
    profiles["timeindex"] = pd.to_datetime(profiles["timeindex"])
    profiles = profiles[profiles["timeindex"].isin(time)]
    return profiles


@typechecked
def retrieve_scenario_from_input_data(general_df: pd.DataFrame) -> str:
    scenario = general_df.loc[general_df["label"] == "scenario", "value"].item()
    return scenario


@typechecked
def matches_scenario(scenario_to_check: str, scenario_wanted: str) -> bool:
    """
    Checks wether the string "scenario to check" is either "all" or
    includes the "scenario_wanted".
    "scenario_wanted" should be the scenario to be optimized,
    and "scenario_to_check" a scenario field
    from the input data.
    """
    return scenario_to_check == "all" or scenario_wanted in scenario_to_check


@typechecked
def filter_input_data_by_scenario(
    sinks: pd.DataFrame,
    sources: pd.DataFrame,
    converters: pd.DataFrame,
    storage: pd.DataFrame,
    scenario_wanted: str,
):
    dfs = {
        "sinks": sinks,
        "sources": sources,
        "converters": converters,
        "storage": storage,
    }
    dfs = {
        name: df[df["scenario"].apply(matches_scenario, args=(scenario_wanted,))]
        for name, df in dfs.items()
    }
    return dfs["sinks"], dfs["sources"], dfs["converters"], dfs["storage"]
