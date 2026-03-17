import matplotlib
import pandas as pd
from pyromof.load_duration_curve import (
    get_data_csv,
    sort_values_descending,
    plot_load_duration_curve,
)

matplotlib.use("Agg")


def test_get_data_csv(tmp_path):
    csv = tmp_path / "test.csv"
    df = pd.DataFrame({"A": [1, 2, 3]})
    df.to_csv(csv, sep=";", index=False)
    result = get_data_csv(str(csv), separator=";", parse_dates=False, target_column="A")
    assert list(result) == [1, 2, 3]


def test_sort_values_descending():
    column = pd.Series([3, 1, 2])
    sorted_column = sort_values_descending(column)
    assert list(sorted_column) == [3, 2, 1]


def test_plot_load_duration_curve(tmp_path):
    column = pd.Series([3, 2, 1])
    save_path = tmp_path / "test_plot.png"
    plot_load_duration_curve(column, "x-title", "y-title", "title", str(save_path))
    assert save_path.exists()
