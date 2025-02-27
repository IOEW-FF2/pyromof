import os
import pandas as pd
import re


def check_type(object, type_wanted):
    if not isinstance(object, type_wanted):
        raise TypeError(
            "Expected {0}; got {1}".format(type_wanted, type(object).__name__)
        )


def retreive_scenario_from_results(es):
    scenario = es.results["scenario"]
    investment = es.results["investment"]
    return scenario, investment


def convert_tuple_columnnames_to_strings(df):
    df.columns = [" to ".join(x) for x in df.columns]
    return df


def filter_cost_items_from_scalar_data(scalar_data):
    filtered = scalar_data[
        (~scalar_data["type"].str.contains("objective \\[Euros\\]", regex=True))
        & scalar_data["type"].str.contains("Euros", regex=False)
    ]
    return filtered


def prepare_cost_scalars_for_plotting(folder_name, file_name, scenario):
    """
    Reads in the scalars from a csv file, filters for cost components and multiplies by -1
    """
    scalar_data = pd.read_csv(
        os.path.join(folder_name, file_name), sep=";", index_col=0
    )
    scalcosts = filter_cost_items_from_scalar_data(scalar_data)
    scalcosts.loc[:, scenario] = scalcosts.loc[:, "value"] * -1
    scalcosts.drop("value", axis=1, inplace=True)
    # TODO: Differentiate between annuity, epc and upfront investment costs and
    # clarify in the plot what is meant
    return scalcosts


def filter_bus_in_string(string):
    pattern = r"b_[^ ]+"  # Matches 'b_' followed by one or more non-space characters
    match = re.search(pattern, string)
    return match.group(0) if match else None
