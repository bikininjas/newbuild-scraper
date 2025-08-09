"""Data loading helpers (legacy CSV history loader retained)."""

import pandas as pd


def load_history(csv_path):  # minimal move
    return pd.read_csv(csv_path, encoding="utf-8")
