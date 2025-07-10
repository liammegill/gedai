"""
Pre-process ADS-B data and create a pandas DataFrame.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"


# imports
from typing import Callable, overload, Union
from functools import wraps
import pandas as pd
import openap
from traffic.core import Flight


def assign_to_flight(
    func: Callable[[pd.DataFrame, ...], pd.DataFrame]
) -> Callable[..., Flight]:
    """
    Decorator that allows a DataFrame-transforming function to be applied
    directly to a Flight object, and automatically updates the Flight's
    data with any new columns returned by the function.

    The decorated function must:
    - Take a pandas DataFrame (typically `flight.data`) as its first argument.
    - Return a DataFrame that includes any new columns to be assigned.

    When used, the decorated function can be called with a Flight object
    as its first argument, and the resulting Flight will have the new
    columns added via `.assign()`.

    Args:
        func: A function that modifies a DataFrame and returns it with
              additional columns to assign.

    Returns:
        A callable that accepts a Flight object and returns a new Flight
        with the updated data.

    Example:
        @assign_to_flight
        def calculate_distance(df):
            df["distance"] = ...
            return df

        new_flight = calculate_distance(flight)
    """

    @wraps(func)
    def wrapper(flight: Flight, *args, **kwargs) -> Flight:
        df = flight.data.copy()
        updated_df = func(df, *args, **kwargs)

        # Only assign new columns
        new_columns = updated_df.columns.difference(flight.data.columns)
        if not new_columns.any():
            return flight

        return flight.assign(**{col: updated_df[col] for col in new_columns})

    return wrapper


@overload
def calculate_distance(obj: pd.DataFrame) -> pd.DataFrame: ...


@overload
def calculate_distance(obj: Flight) -> Flight: ...


def calculate_distance(
    obj: Union[pd.DataFrame, Flight]
) -> Union[pd.DataFrame, Flight]:
    """Add distance column to a DataFrame of Flight.

    Args:
        obj (Union[pd.DataFrame, Flight]): Flight data

    Returns:
        Union[pd.DataFrame, Flight]: Object with added "distance" column [km]
    """
    is_flight = hasattr(obj, "data")
    df = obj.data.copy() if is_flight else obj.copy()

    # pre-conditions
    req_cols = ["timestamp", "latitude", "longitude", "altitude"]
    missing = [col for col in req_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    df["distance"] = (
        openap.aero.distance(
            df["latitude"].shift(1),
            df["longitude"].shift(1),
            df["latitude"],
            df["longitude"],
            df["altitude"] * openap.aero.ft,
        )
        / 1e3
    )  # km
    df["distance"] = df["distance"].fillna(0.0)

    return obj.assign(distance=df["distance"])
