import pandas as pd
import numpy as np


# ---------------------------------------------------------
# PaySim Columns
# ---------------------------------------------------------

NUMERIC_COLUMNS = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud"
]


REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest"
]


TRANSACTION_TYPES = [
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER"
]


# ---------------------------------------------------------
# Clean Data
# ---------------------------------------------------------

def clean_data(df):
    """
    Clean a PaySim DataFrame.

    Operations:
    - Remove duplicate rows
    - Convert numerical columns to numeric
    - Remove rows with missing important values
    - Remove negative transaction/balance values
    - Clean transaction type
    """

    # Create a copy so the original DataFrame is not modified
    df = df.copy()

    # -----------------------------------------------------
    # Remove duplicate rows
    # -----------------------------------------------------

    df = df.drop_duplicates()

    # -----------------------------------------------------
    # Convert numerical columns
    # -----------------------------------------------------

    for column in NUMERIC_COLUMNS:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # -----------------------------------------------------
    # Clean transaction type
    # -----------------------------------------------------

    if "type" in df.columns:

        df["type"] = (
            df["type"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # -----------------------------------------------------
    # Remove rows with missing required values
    # -----------------------------------------------------

    existing_required = [
        column
        for column in REQUIRED_COLUMNS
        if column in df.columns
    ]

    df = df.dropna(
        subset=existing_required
    )

    # -----------------------------------------------------
    # Remove invalid negative values
    # -----------------------------------------------------

    balance_columns = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest"
    ]

    for column in balance_columns:

        if column in df.columns:

            df = df[df[column] >= 0]

    # -----------------------------------------------------
    # Remove invalid transaction types
    # -----------------------------------------------------

    if "type" in df.columns:

        df = df[
            df["type"].isin(TRANSACTION_TYPES)
        ]

    # Reset index
    df = df.reset_index(drop=True)

    return df


# ---------------------------------------------------------
# Encode Transaction Type
# ---------------------------------------------------------

def encode_transaction_type(df):
    """
    Encode PaySim transaction type using fixed one-hot
    columns.

    Fixed columns:
    - type_CASH_IN
    - type_CASH_OUT
    - type_DEBIT
    - type_PAYMENT
    - type_TRANSFER
    """

    df = df.copy()

    if "type" not in df.columns:
        return df

    # Create fixed one-hot columns
    for transaction_type in TRANSACTION_TYPES:

        column_name = f"type_{transaction_type}"

        df[column_name] = (
            df["type"] == transaction_type
        ).astype("int8")

    # Remove original categorical column
    df = df.drop(
        columns=["type"]
    )

    return df


# ---------------------------------------------------------
# Prepare Complete DataFrame
# ---------------------------------------------------------

def prepare_data(df):
    """
    Complete preprocessing pipeline.

    Steps:
    1. Clean data
    2. Encode transaction type
    3. Return processed DataFrame
    """

    df = clean_data(df)

    df = encode_transaction_type(df)

    return df


# ---------------------------------------------------------
# Prepare Chunk
# ---------------------------------------------------------

def prepare_chunk(df):
    """
    Prepare one chunk of PaySim data.

    This function is useful when reading the large PaySim
    dataset using pandas chunksize.
    """

    return prepare_data(df)


# ---------------------------------------------------------
# Process PaySim CSV in Chunks
# ---------------------------------------------------------

def process_paysim_in_chunks(
    input_file,
    output_file,
    chunksize=100000
):
    """
    Process a PaySim CSV file in chunks.

    Parameters
    ----------
    input_file : str
        Path to original PaySim CSV.

    output_file : str
        Path where processed CSV will be saved.

    chunksize : int
        Number of rows processed at a time.
    """

    first_chunk = True

    for chunk in pd.read_csv(
        input_file,
        chunksize=chunksize
    ):

        # Process current chunk
        processed_chunk = prepare_chunk(chunk)

        # Save processed chunk
        processed_chunk.to_csv(
            output_file,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False
        )

        first_chunk = False

    print(
        f"Processed PaySim data saved to: {output_file}"
    )