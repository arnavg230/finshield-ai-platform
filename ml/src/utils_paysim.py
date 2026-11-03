import os
import pandas as pd
import numpy as np


def check_file_exists(file_path):
    """
    Check whether a file exists.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    return True


def load_data_in_chunks(
    file_path,
    chunksize=500000
):
    """
    Load a CSV file using chunks.
    """

    check_file_exists(file_path)

    return pd.read_csv(
        file_path,
        chunksize=chunksize
    )


def check_missing_values(df):
    """
    Return missing-value summary.
    """

    summary = pd.DataFrame({
        "Missing Values": df.isnull().sum(),
        "Missing Percentage":
            (df.isnull().sum() / len(df)) * 100
    })

    return summary


def check_infinite_values(df):
    """
    Count infinite values in numerical columns.
    """

    numeric_df = df.select_dtypes(
        include=np.number
    )

    return np.isinf(numeric_df).sum()


def save_dataframe(df, file_path):
    """
    Save a DataFrame to CSV.
    """

    directory = os.path.dirname(file_path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    df.to_csv(
        file_path,
        index=False
    )


def load_feature_names(file_path):
    """
    Load feature names from a text file.
    """

    check_file_exists(file_path)

    with open(file_path, "r") as file:
        features = [
            line.strip()
            for line in file
            if line.strip()
        ]

    return features


def calculate_fraud_rate(y_true, y_pred):
    """
    Calculate the percentage of predicted
    fraudulent transactions.
    """

    total = len(y_pred)

    if total == 0:
        return 0

    fraud_count = np.sum(
        np.asarray(y_pred) == 1
    )

    return (fraud_count / total) * 100