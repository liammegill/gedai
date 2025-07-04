"""
Functions to identify and split by legs.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"


# imports
from datetime import timedelta
from typing import Iterator
import pandas as pd
import openap
from traffic.core import Flight
from traffic.core.iterator import flight_iterator

from ..core import assign_to_flight


@flight_iterator
def split_by_leg(flight: Flight, source: str="custom") -> Iterator["Flight"]:
    """Split Flight by the leg number using the flight_iterator decorator.

    Args:
        flight (Flight): Flight to be split
        source (str): ADS-B source (e.g., "adsb_exchange").
            Defaults to "custom".

    Yields:
        Flight: Flight split by the leg.
    """
    if "phase" not in flight.data.columns:
        flight = flight.phases()

    if "leg" not in flight.data.columns:
        flight = identify_legs(flight, source)

    for _, leg_df in flight.data.groupby("leg"):
        if len(leg_df) >= 2:
            yield Flight(leg_df)


def leg_split_condition(f1: Flight, f2: Flight) -> bool:
    """Condition for the .split() method of traffic's Flight object.

    Args:
        f1 (Flight): Flight 1
        f2 (Flight): Flight 2

    Raises:
        ValueError: If the column "leg" is not found.

    Returns:
        bool: Where to split the data.
    """
    try:
        return f1.data["leg"].iloc[-1] != f2.data["leg"].iloc[0]
    except KeyError as e:
        raise ValueError("Missing 'leg' column in Flight data.") from e


@assign_to_flight
def identify_legs(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Applies leg identification to the input DataFrame, modifying it in place.
    The function adds a new column "leg" with integers denoting the
    corresponding leg.

    Args:
        df (pd.DataFrame): DataFrame containing ADS-B data.
        source (str): ADS-B source (e.g., "adsb_exchange").

    Returns:
        pd.DataFrame: DataFrame with an added "leg" column identifying segments.

    Raises:
        ValueError: If unknown source is provided.
    """

    if source == "adsb_exchange":
        # use ADS-B Exchange's internal leg identification
        return _identify_legs_adsbexchange(df)

    if source == "custom":
        # use custom requirements
        df = _identify_legs_custom(df)
        df = _filter_short_legs(df)  # filter out short legs
        return df

    raise ValueError(
        f"No leg detection logic implemented for source: {source}"
    )


def _identify_legs_adsbexchange(df: pd.DataFrame) -> pd.DataFrame:
    """Identify legs using the "flags" data from ADS-B Exchange.

    Args:
        df (pd.DataFrame): DataFrame containing ADS-B data.

    Returns:
        pd.DataFrame: DataFrame modified in place to contain new column "leg".
    """
    if "flags" not in df.columns:
        raise ValueError("Missing column 'flags' in DataFrame.")
    leg_flags = (df["flags"] & 2).astype(bool)
    df["leg"] = leg_flags.cumsum()
    return df


def _identify_legs_custom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify legs using custom conditions:
    1) Ground contact
    2) Aircraft is between 0 and 10,000 ft and signal is lost for > 5 min
    3) Aircraft is above 10,000 ft and signal is lost for > 10 h

    Args:
        df (pd.DataFrame): DataFrame containing ADS-B data.

    Returns:
        pd.DataFrame: DataFrame modified in place to contain new column "leg".
    """
    # pre-conditions
    req_cols = ["timestamp", "altitude", "phase"]
    missing = [col for col in req_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    # shifted columns for previous state
    prev_alt = df["altitude"].shift(1)
    prev_phase = df["phase"].shift(1)
    delta_t = df["timestamp"] - df["timestamp"].shift(1)

    # condition 1: ground contact
    cond_1 = (prev_phase != "GROUND") & (df["phase"] == "GROUND")

    # condition 2: 0 < alt < 10 kft and > 5 min
    low_alt = ((df["altitude"] > 0) & (df["altitude"] < 10000)) | \
              ((prev_alt > 0) & (prev_alt < 10000))
    cond_2 = low_alt & (delta_t > timedelta(minutes=5))

    # condition 3: alt >= 10 kft and > 10 h
    high_alt = (df["altitude"] >= 10000) | (prev_alt >= 10000)#
    cond_3 = high_alt & (delta_t > timedelta(hours=10))

    # combine conditions
    leg_breaks = cond_1 | cond_2 | cond_3
    leg_breaks.iloc[0] = True

    # assign to df
    df["leg"] = leg_breaks.astype("int32").cumsum() - 1

    return df


def _filter_short_legs(
    df: pd.DataFrame,
    min_duration: int=5,
    min_dist: float=3.0
) -> pd.DataFrame:
    """Apply simple filter to remove short legs.

    Args:
        df (pd.DataFrame): DataFrame containing ADS-B data.
        min_duration_min (int, optional): Minimum leg duration [min].
            Defaults to 5.
        min_dist_km (float, optional): Minimum leg distance [km].
            Defaults to 3.0.

    Returns:
        pd.DataFrame: DataFrame where short legs have been filtered out.
    """
    keep_legs = []
    for _, leg_df in df.groupby("leg"):
        if len(leg_df) < 2:
            continue

        # check leg duration
        duration = leg_df["timestamp"].iloc[-1] - leg_df["timestamp"].iloc[0]
        if duration < timedelta(minutes=min_duration):
            continue

        # check leg distance
        dist = openap.aero.distance(
            leg_df["latitude"].iloc[0], leg_df["longitude"].iloc[0],
            leg_df["latitude"].iloc[-1], leg_df["longitude"].iloc[-1],
        )
        if dist < min_dist:
            continue

        keep_legs.append(leg_df)

    return pd.concat(keep_legs, ignore_index=True)
