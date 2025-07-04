"""
Pre-process ADS-B data and create a pandas DataFrame.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"


# imports
import pandas as pd
import openap


def create_dataframe(
    data: dict,
    metadata: dict,
    source: str,
) -> pd.DataFrame:
    """
    Create a standardised DataFrame from raw ADS-B data and metadata such that
    it can be loaded into traffic.

    Args:
        data (dict): Parsed JSON data, including 'trace'.
        metadata (dict): Associated metadata like ICAO, registration, timestamp.
        source (str): Source of the ADS-B data (e.g., "adsb_exchange").

    Returns:
        pd.DataFrame: A standardised, processed DataFrame.
    """

    # pre-conditions
    if not isinstance(data, dict) or "trace" not in data:
        raise ValueError(
            "Invalid input: 'data' must be a dict containing a 'trace' key."
        )
    if not isinstance(metadata, dict):
        raise ValueError("Invalid input: 'metadata' must be a dict.")
    if source not in ["adsb_exchange"]:
        raise ValueError("Unsupported ADS-B source.")

    df = pd.DataFrame(data["trace"])  # TODO: this may need to be source-specific
    df = standardise_columns(df, source)
    df = df.dropna(
        subset=["altitude", "groundspeed", "vertical_rate"], ignore_index=True
    ).copy()
    df = add_metadata_columns(df, metadata, source)
    df = df.convert_dtypes(dtype_backend="pyarrow")  # convert dtype to pyarrow

    return df


def standardise_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Standardise column names and order of a DataFrame in place for internal
    consistency.

    Args:
        df (pd.DataFrame): Raw trace DataFrame.
        source (str): Source of the ADS-B data (e.g., "adsb_exchange").

    Returns:
        pd.DataFrame: DataFrame with consistent column names, modified in place.

    Raises:
        ValueError: If the source is unknown or unsupported.
    """
    if source == "adsb_exchange":
        # check input
        expected_columns = 14  # adsb_exchange format
        if df.shape[1] < expected_columns:
            raise ValueError(
                f"Expected {expected_columns} columns, got {df.shape[1]}"
            )
        # identify columns
        df.columns = [
            "dtime", "latitude", "longitude", "altitude", "groundspeed", 
            "track", "flags", "vertical_rate", "extra_data", "source",
            "col1", "col2", "col3", "col4"
        ]
        df = df[[
            "dtime", "latitude", "longitude", "altitude", "groundspeed",
            "track", "flags", "vertical_rate"
        ]].copy()
        # update longitude and altitude
        df["longitude"] = df["longitude"] % 360.0
        with pd.option_context("future.no_silent_downcasting", True):
            df["altitude"] = df["altitude"].replace("ground", 0.0).astype(float)
        # calculate pressure
        df["pressure"] = openap.aero.pressure(df["altitude"] * openap.aero.ft)

    else:
        raise ValueError(f"Unsupported source: {source}")

    return df


def add_metadata_columns(
    df: pd.DataFrame, metadata: dict, source: str
) -> pd.DataFrame:
    """Add relevant metadata fields to a DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame.
        metadata (dict): Associated metadata like ICAO, registration, timestamp.
        source (str): Source of the ADS-B data (e.g., "adsb_exchange").

    Returns:
        pd.DataFrame: DataFrame with metadata, modified in place.
    """
    if source == "adsb_exchange":
        # ensure keys are present
        req_keys = ["timestamp", "t", "r", "icao"]
        missing = [k for k in req_keys if k not in metadata]
        if missing:
            raise KeyError(f"Missing required metadata keys: {missing}")

        # add metadata to df
        df["timestamp"] = pd.to_datetime(
            metadata["timestamp"] + df["dtime"], unit="s", utc=True
        )
        df["type"] = metadata.get("t")
        df["registration"] = metadata.get("r")
        df["icao24"] = metadata.get("icao")

    else:
        raise ValueError(f"Unsupported source: {source}")

    return df
