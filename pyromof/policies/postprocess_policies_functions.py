import pandas as pd

from pyromof.policies.implement_policies import (
    receive_and_refine_electricity_price_data,
)


def receive_data(scenario: str, data: dict) -> tuple[pd.Series, pd.Series, float, float]:

    policies = data["policies"]

    pyrolysis_electricity_output = pd.read_csv(
        f"./results/{scenario}/results/sequences.csv", sep=";", index_col=0, parse_dates=True
    )["b_electricity to electricity_grid"]

    electricity_price = receive_and_refine_electricity_price_data(data["profiles"])

    return (electricity_price, pyrolysis_electricity_output, policies)


def receive_capex_data(scenario, data):

    policies = data["policies"]
    converters = data["converters"]

    yearly_biochar_output = (
        1
        / 1000
        * pd.read_csv(
            f"./results/{scenario}/results/sequences.csv", sep=";", index_col=0, parse_dates=True
        )["b_biochar to biochar_market"].sum()
    )
    # Es wird ein Auslegungswert für den jährlichen Biochar output benötigt
    # -> ist der 59,9 Wert der stündlich angelegte output Wert?
    # aktuell wird dann nur Monatswert berechnet

    # zweite Möglcihkeit:
    yearly_biochar_output = (
        8.76 * converters.loc[converters["label"] == "pyrolysis", "nominal_capacity"].values[0]
    )
    # 8.76 da stündlcher Wert * 8760 Stunden im Jahr und /1000 von kg zu t

    return policies, converters, yearly_biochar_output
