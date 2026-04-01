import argparse

import matplotlib.pyplot as plt
import pandas as pd


def get_data_csv(scenario: str) -> pd.DataFrame:
    """Read data from CSV file of the chosen scenario."""
    file_path = f"./results/{scenario}/results/sequences.csv"
    separator = ";"
    parse_dates = True
    target_columns = [
        "b_electricity to electricity_grid",
        "b_biomass_dry to pyrolysis",
    ]

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_columns]


def sort_values_descending(df: pd.DataFrame, column: str) -> pd.Series:
    """Sort values in descending order."""
    s = pd.to_numeric(df[column])
    return s.sort_values(ascending=False)


def plot_load_duration_curve(sorted_column, xlabel, ylabel, title, save_path):
    """Plot the load duration curve."""
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(sorted_column)), sorted_column.values)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.savefig(save_path)
    plt.close()


def main(scenario: str) -> None:
    """Execute the load duration curve generation."""
    columns = get_data_csv(scenario)

    descending_power_data = sort_values_descending(columns, "b_electricity to electricity_grid")
    descending_biomass_data = sort_values_descending(columns, "b_biomass_dry to pyrolysis")

    plot_load_duration_curve(
        sorted_column=descending_power_data,
        xlabel="Hours",
        ylabel="Electricity feed-in (kWh)",
        title=f"Scenario {scenario}: Load duration curve - Power",
        save_path=f"./results/{scenario}/results/load_duration_curve_power.png",
    )
    plot_load_duration_curve(
        sorted_column=descending_biomass_data,
        xlabel="Hours",
        ylabel="Biomass input (kg)",
        title=f"Scenario {scenario}: Load duration curve - Biomass",
        save_path=f"./results/{scenario}/results/load_duration_curve_biomass.png",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        required=True,
        help="Name of the scenario, e.g. stromflex_h2",
    )
    args = parser.parse_args()
    main(args.scenario)
