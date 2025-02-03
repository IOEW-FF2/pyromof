def check_type(object, type_wanted):
    if not isinstance(object, type_wanted):
        raise TypeError(
            "Expected {0}; got {1}".format(type_wanted, type(object).__name__)
        )


def retreive_scenario_from_results(es):
    scenario = es.results["scenario"]
    if "investment" in scenario:
        investment = True
    else:
        investment = False
    return scenario, investment


def convert_tuple_columnnames_to_strings(df):
    df.columns = [" to ".join(x) for x in df.columns]
    return df
