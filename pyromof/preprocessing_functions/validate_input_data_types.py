import numpy as np
import pandas as pd


def validate_input_data_column_types(input_file, sheet_rules, prefix_rules):
    """
    Validates column types of input data sheets based on predefined rules.
    """
    errors = []

    # implement column type rules

    def infer_dtype(sheet, col):
        rules = sheet_rules.get(sheet, {})
        if col in rules.get("exceptions", {}):
            return rules["exceptions"][col]
        for prefix, dtype in prefix_rules.items():
            if col.startswith(prefix):
                return dtype
        return rules.get("default")

    def check_type(col_data, dtype, profile_cols=None):

        # get type specification for error feedback
        non_na = col_data.dropna()
        unique_types = set(type(v) for v in non_na)
        actual_type = str(col_data.dtype)

        def get_type_mix():
            return (
                ", ".join(sorted(t.__name__ for t in unique_types))
                if len(unique_types) > 1 or actual_type == "object"
                else actual_type
            )

        # define function to validate str|list(str) data type
        def check_str_list():
            for idx, val in col_data.items():
                if not pd.isna(val) and not isinstance(val, str):
                    return f"Non-string at {idx} [actual={actual_type} mix={get_type_mix()}]"
                if isinstance(val, str) and not all(
                    isinstance(v, str) for v in [v.strip() for v in val.split(",")]
                ):
                    return f"Invalid list at {idx} [actual={actual_type} mix={get_type_mix()}]"
            return None

        # define function to validate numeric|str data type
        def check_numeric_str():
            if not (
                pd.api.types.is_numeric_dtype(col_data)
                or pd.api.types.is_string_dtype(col_data)
                or (
                    actual_type == "object"
                    and unique_types.issubset({int, float, str, np.integer, np.floating})
                )
            ):
                return f"Invalid type [actual={actual_type} mix={get_type_mix()}]"
            if pd.api.types.is_string_dtype(col_data) or actual_type == "object":
                for idx, val in col_data.items():
                    if pd.isna(val):
                        continue
                    if isinstance(val, str):
                        for item in val.split(","):
                            if item.strip() not in profile_cols:
                                return (
                                    f"Profile '{item.strip()}' not found "
                                    f"[actual={actual_type} mix={get_type_mix()}]"
                                )
                    elif not isinstance(val, (int, float, np.integer, np.floating)):
                        return (
                            f"Unsupported type at {idx} [actual={actual_type} mix={get_type_mix()}]"
                        )
            return None

        # define function to validate str, numeric, and bool data types
        def check_other_types(dtype_key):
            type_funcs = {
                "str": lambda: (
                    pd.api.types.is_string_dtype(col_data)
                    or (actual_type == "object" and unique_types.issubset({str}))
                ),
                "numeric": lambda: (
                    pd.api.types.is_numeric_dtype(col_data)
                    or (
                        actual_type == "object"
                        and unique_types.issubset({int, float, np.integer, np.floating})
                    )
                ),
                "bool": lambda: (
                    pd.api.types.is_bool_dtype(col_data)
                    or (actual_type == "object" and unique_types.issubset({bool}))
                ),
            }
            return (
                f"Must be {dtype_key} [actual={actual_type} mix={get_type_mix()}]"
                if not type_funcs[dtype_key]()
                else None
            )

        # create dictionary to apply type validation functions
        type_checks = {
            "str|list[str]": check_str_list,
            "numeric|str": check_numeric_str,
            "str": lambda: check_other_types("str"),
            "numeric": lambda: check_other_types("numeric"),
            "bool": lambda: check_other_types("bool"),
        }

        return type_checks.get(
            dtype, lambda: f"Unknown type '{dtype}' [actual={actual_type} mix={get_type_mix()}]"
        )()

    try:
        profiles_df = pd.read_excel(input_file, sheet_name="profiles")
        profile_columns = set(profiles_df.columns)
    except Exception:
        profile_columns = set()

    # initiate loop for column type calidation
    for sheet, rules in sheet_rules.items():
        try:
            df = pd.read_excel(input_file, sheet_name=sheet)
            ignore = set(rules.get("ignore", []))
            cols = [c for c in df.columns if c not in ignore]

            # row-wise validation for "general" sheet
            if sheet == "general":
                row_rules = rules.get("row_rules", {})
                for idx, row in df.iterrows():
                    label = row.get("label")
                    value = row.get("value")
                    if pd.isna(label) or pd.isna(value):
                        continue
                    expected_dtype = row_rules.get(str(label))
                    if expected_dtype:
                        if expected_dtype == "str" and not isinstance(value, str):
                            errors.append(f"{sheet}/row {idx}/value: Must be string")
                        elif expected_dtype == "numeric" and not isinstance(value, (int, float)):
                            errors.append(f"{sheet}/row {idx}/value: Must be numeric")
                        elif expected_dtype == "datetime":
                            if pd.isna(pd.to_datetime(value, errors="coerce")):
                                errors.append(f"{sheet}/row {idx}/value: Must be datetime")
                continue

            # create error messages
            for col in cols:
                dtype = infer_dtype(sheet, col)
                error = check_type(df[col], dtype, profile_columns)
                if error:
                    errors.append(f"{sheet}/{col}: {error}")
        except Exception as e:
            errors.append(f"Error in {sheet}: {e}")

    if errors:
        print("\nValidation errors:")
        for err in errors:
            print(f"- {err}")
        raise ValueError("Validation failed")
    else:
        print("All types valid.")
