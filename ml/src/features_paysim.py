import pandas as pd
import numpy as np


def create_balance_features(df):
    """
    Create features based on sender and receiver balances.
    """

    df = df.copy()

    # Sender balance change
    df["origin_balance_change"] = (
        df["oldbalanceOrg"]
        - df["newbalanceOrig"]
    )

    # Receiver balance change
    df["destination_balance_change"] = (
        df["newbalanceDest"]
        - df["oldbalanceDest"]
    )

    return df


def create_transaction_difference_features(df):
    """
    Create features comparing transaction amount
    with account balance changes.
    """

    df = df.copy()

    # Difference between transaction amount
    # and sender balance change
    df["origin_error"] = (
        df["amount"]
        - df["origin_balance_change"]
    )

    # Difference between transaction amount
    # and receiver balance change
    df["destination_error"] = (
        df["amount"]
        - df["destination_balance_change"]
    )

    return df


def create_ratio_features(df):
    """
    Create transaction-to-balance ratio features.
    """

    df = df.copy()

    # Amount relative to sender's balance
    df["amount_to_origin_balance"] = (
        df["amount"]
        / (df["oldbalanceOrg"] + 1)
    )

    # Amount relative to receiver's balance
    df["amount_to_destination_balance"] = (
        df["amount"]
        / (df["oldbalanceDest"] + 1)
    )

    return df


def create_features(df):
    """
    Create all PaySim engineered features.
    """

    df = df.copy()

    df = create_balance_features(df)

    df = create_transaction_difference_features(df)

    df = create_ratio_features(df)

    return df