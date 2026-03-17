import pandas as pd
import matplotlib.pyplot as plt


def get_data_csv(
    file_path: str,
    separator: str,
    parse_dates: bool,
    target_column: str,
) -> pd.Series:

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_column]


def sort_values_descending(column) -> pd.Series:
    sorted_column = column.sort_values(ascending=False)
    return sorted_column


def plot_load_duration_curve(sorted_column, xlabel, ylabel, title, save_path):
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(sorted_column)), sorted_column.values)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.savefig(save_path)
    plt.show()


# receive data for power and biomass load

power_data = get_data_csv(
    file_path="./results/stromflex_h2/results/sequences.csv",
    separator=";",
    parse_dates=True,
    target_column="b_electricity to electricity_grid",
)
biomass_data = get_data_csv(
    file_path="./results/stromflex_h2/results/sequences.csv",
    separator=";",
    parse_dates=True,
    target_column="b_biomass_dry to pyrolysis",
)


# sort the data in descending order

descending_power_data = sort_values_descending(power_data)
descending_biomass_data = sort_values_descending(biomass_data)


# plot the load duration curves for power and biomass load

power_load_duration_curve = plot_load_duration_curve(
    sorted_column=descending_power_data,
    xlabel="Hours",
    ylabel="Injected Energy",
    title="Load duration curve - Power",
    save_path="./results/stromflex_h2/results/load_duration_curve_power.png",
)
biomass_duration_curve = plot_load_duration_curve(
    sorted_column=descending_biomass_data,
    xlabel="Hours",
    ylabel="Injected Biomass",
    title="Load duration curve - Biomass",
    save_path="./results/stromflex_h2/results/load_duration_curve_biomass.png",
)


power_load_duration_curve
biomass_duration_curve


exit()
