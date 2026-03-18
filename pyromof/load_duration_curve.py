import argparse
import pandas as pd
import matplotlib.pyplot as plt

    # function to read data from CSV file of the chosen scenario
def get_data_csv(scenario: str) -> pd.DataFrame:
    file_path = f"./results/{scenario}/results/sequences.csv"
    separator = ";"
    parse_dates = True
    target_columns = [
        "b_electricity to electricity_grid",
        "b_biomass_dry to pyrolysis",
    ]

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_columns]

    # function to sort values in descending order
def sort_values_descending(df: pd.DataFrame, column: str) -> pd.Series:
    s = pd.to_numeric(df[column])
    return s.sort_values(ascending=False)

    # function to plot the load duration curve
def plot_load_duration_curve(sorted_column, xlabel, ylabel, title, save_path):
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(sorted_column)), sorted_column.values)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.savefig(save_path)
    plt.close()

    # main function to execute the load duration curve generation
def main(scenario: str) -> None:
    columns = get_data_csv(scenario)

    descending_power_data = sort_values_descending(
        columns, "b_electricity to electricity_grid"
    )
    descending_biomass_data = sort_values_descending(
        columns, "b_biomass_dry to pyrolysis"
    )

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
        ylabel="Injected Biomass (kg)",
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
