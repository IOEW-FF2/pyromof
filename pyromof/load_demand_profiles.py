import datetime
import os
from pathlib import Path
import pandas as pd
from demandlib import bdew

# read example temperature series
filename = "example_data.csv"
thisdir = os.getcwd()
ROOT_PATH = Path(__file__).parent.parent
dirname = os.path.join(ROOT_PATH, "raw_data")
datapath = os.path.join(dirname, filename)

temperature = pd.read_csv(datapath)["temperature"]

ann_demands_per_type = {"efh": 25000, "mfh": 80000, "ghd": 140000}

# Create DataFrame for 2025
demand = pd.DataFrame(
    index=pd.date_range(datetime.datetime(2025, 1, 1, 0), periods=8760, freq="h")
)

# Multi family house (mfh: Mehrfamilienhaus)
demand["mfh"] = bdew.HeatBuilding(
    demand.index,
    temperature=temperature,
    shlp_type="MFH",
    building_class=2,
    wind_class=0,
    annual_heat_demand=ann_demands_per_type["mfh"],
    name="MFH",
).get_normalized_bdew_profile()

demand.to_csv("heat_profile.csv")
