def implement_storage_subsidies(storage, policies):

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

    active_policies = (
        policies.loc[policies["activate"] == "x", ["policy", "value 1"]]
        .set_index("policy")["value 1"]
        .to_dict()
    )

    for storage_label, policy_name in subsidy_configs["lump_sum"].items():
        if policy_name not in active_policies:
            continue

        subsidy = active_policies[policy_name]

        mask = storage["label"] == storage_label
        storage.loc[mask, "capex"] -= subsidy

    for storage_label, policy_name in subsidy_configs["percentage"].items():
        if policy_name not in active_policies:
            continue

        percentage = active_policies[policy_name]
        subsidy_factor = 1 - (percentage / 100)

        storage_subsidy = storage["label"] == storage_label
        storage.loc[storage_subsidy, "capex"] *= subsidy_factor

    return storage
