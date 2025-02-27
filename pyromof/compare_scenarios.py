import os
import plotly.graph_objects as go
import pandas as pd
import helpers
from pathlib import Path


def merge_scalars_from_scenarios(scenarios):
    """
    This script takes a list of scenario names and processes and joins their scalar data.
    The resulting dataframe has the following format:
    |variable                   |type                           |{scenario_name_1}|{scenario_name_2}|
    b_biochar to biochar_market | sum of variable costs [Euros] | 10.7            |1.4e-01          |
    Non-existing numbers are filled with zeros.
    """

    dataframes = []
    for scenario in scenarios:
        SCENARIO_RESULTS = os.path.join(RESULTS, scenario, "results")
        scalcosts = helpers.prepare_cost_scalars_for_plotting(
            SCENARIO_RESULTS, "scalar_results.csv", scenario
        )
        dataframes.append(scalcosts)
    merged_df = dataframes[0].copy()

    for df in dataframes[1:]:
        merged_df = pd.merge(merged_df, df, on=["variable", "type"], how="outer")

    print(merged_df)
    return merged_df


def plot_cost_scalars_comparison(multiscenario_scalcosts, scenarios):

    fig = go.Figure()

    for variable in multiscenario_scalcosts.variable:
        fig.add_trace(
            go.Bar(
                name=variable,
                x=scenarios,
                y=multiscenario_scalcosts.loc[
                    multiscenario_scalcosts["variable"] == variable, scenarios
                ].iloc[0, :],
                hoverinfo="name+y"
            )
        )

    # Add points for total
    for scenario in scenarios:
        total = multiscenario_scalcosts[scenario].sum()
        fig.add_trace(
            go.Scatter(
                x=[scenario],
                y=[total],
                mode="markers",
                marker_symbol="diamond",
                marker_color="black",
                marker=dict(size=15),
                hoverinfo="text+y",
                text=["Total"],
                name="Total",
            )
        )

    # Plot negative values below the x-axis
    fig.update_layout(barmode="relative")
    # Save plot as html
    fig.write_html(os.path.join(RESULTS, "cost_scalars.html"))


if __name__ == "__main__":
    ROOT_PATH = Path(__file__).parent.parent
    RESULTS = os.path.join(ROOT_PATH, "results")
    # scenarios = [input("For which scenario shall the results be compared? Please enter the scenario names separated by commas. ")]
    scenarios = ["linear", "autarkize"]

    multiscenario_scalcosts = merge_scalars_from_scenarios(scenarios)
    plot_cost_scalars_comparison(multiscenario_scalcosts, scenarios)
