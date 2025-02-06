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