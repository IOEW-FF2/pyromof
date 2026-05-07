from pyromof.preprocessing_functions import preprocessing_input_data


def implement_storage_subsidies(data, active_policies):

    subsidy_configs = {
        "lump_sum": {
            "electricity_storage": "electricity storage lump sum subsidy",
            "heat_storage": "heat storage lump sum subsidy",
            "hydrogen_storage": "hydrogen storage lump sum subsidy",
            "co2_storage": "co2 storage lump sum subsidy",
        },
        "percentage": {
            "electricity_storage": "electricity storage percentage subsidy",
            "heat_storage": "heat storage percentage subsidy",
            "hydrogen_storage": "hydrogen storage percentage subsidy",
            "co2_storage": "co2 storage percentage subsidy",
        },
    }

    for storage_label, policy_name in subsidy_configs["lump_sum"].items():
        if policy_name not in active_policies:
            continue

        subsidy = active_policies[policy_name]

        mask = data["storage"]["label"] == storage_label
        data["storage"].loc[mask, "capex"] -= subsidy

    for storage_label, policy_name in subsidy_configs["percentage"].items():
        if policy_name not in active_policies:
            continue

        percentage = active_policies[policy_name]
        subsidy_factor = 1 - (percentage / 100)

        storage_subsidy = data["storage"]["label"] == storage_label
        data["storage"].loc[storage_subsidy, "capex"] *= subsidy_factor

    return data["storage"]


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    active_policies = (
        data["policies"]
        .loc[data["policies"]["activate"] == "x", ["policy", "value 1"]]
        .set_index("policy")["value 1"]
        .to_dict()
    )
    implement_storage_subsidies(data, active_policies)
