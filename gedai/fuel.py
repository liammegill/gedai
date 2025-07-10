"""
Functions to calculate fuel use.
"""

# imports
from typing import Union, overload

import openap
import pandas as pd
import numpy as np


@overload
def compute_fuel_flow(
    obj: pd.DataFrame,
    fuelflow,
    m_start: float,
    ac: dict,
    retry_with_mtow: bool = True,
    vectorised: bool = True,
) -> pd.DataFrame: ...


@overload
def compute_fuel_flow(
    obj: "Flight",
    fuelflow,
    m_start: float,
    ac: dict,
    retry_with_mtow: bool = True,
    vectorised: bool = True,
) -> "Flight": ...


def compute_fuel_flow(
    obj: Union[pd.DataFrame, "Flight"],
    fuelflow: openap.FuelFlow,
    m_start: float,
    ac: dict,
    retry_with_mtow: bool = True,
    vectorised: bool = True,
) -> Union[pd.DataFrame, "Flight"]:
    """
    Calculate fuel flow based on phase, mass, and aircraft config.

    Accepts either a pandas DataFrame or a Flight object. If given a Flight,
    it returns a new Flight with added fuel-related columns. If given a
    DataFrame, it returns a modified copy.

    Args:
        df (pd.DataFrame): Flight data.
        fuelflow (openap.FuelFlow): Instance of the OpenAP FuelFlow class.
        m_start (float): Initial mass of the aircraft [kg] or fraction of MTOW.
        ac (dict): Aircraft configuration.
        retry_with_mtow (bool, optional): Retry with MTOW if final mass
            is below OEW. Defaults to True.
        vectorised (bool, optional): Use a vectorised method (approximation,
            but up to 100 times faster). Defaults to True.

    Returns:
        Union[pd.DataFrame, Flight]: DataFrame with columns "fuelflow" [kg/s],
            "fuel" [kg], and "dt" [s].

    Raises:
        ValueError: If m_start is invalid or final mass is below OEW.
    """
    is_flight = hasattr(obj, "data")  # check whether it is a flight instance
    df = obj.data.copy() if is_flight else obj.copy()

    mtow = ac["mtow"]
    oew = ac["oew"]

    # interpret m_start
    if m_start > mtow:
        raise ValueError("Initial mass may not be larger than MTOW.")
    if m_start <= 0:
        raise ValueError("Initial mass must be positive.")
    if m_start <= 1:
        m_start = m_start * mtow

    # select function to run
    ff_func = _fuel_flow_vectorised if vectorised else _fuel_flow_iterative

    # calculate fuel flow, fuel and final mass
    ff, fuel, mass = ff_func(df, fuelflow, m_start)

    # check if final mass is below OEW
    if mass[-1] < oew:
        if retry_with_mtow:
            ff, fuel, mass = ff_func(df, fuelflow, mtow)
            if mass[-1] < oew:
                raise ValueError(
                    f"Final mass {mass[-1]:.1f} kg is below OEW {oew:.1f} kg "
                    "even after retrying with MTOW."
                )
        else:
            raise ValueError(
                f"Final mass {mass[-1]:.1f} kg is below OEW {oew:.1f} kg."
            )

    dt = df.timestamp.diff().dt.total_seconds().bfill()
    return obj.assign(fuelflow=ff, fuel=fuel, dt=dt)


def _fuel_flow_iterative(
    df: pd.DataFrame, fuelflow: openap.FuelFlow, m_start: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Iterative fuel flow calculation, updating mass step by step.

    Args:
        df (pd.DataFrame): Flight data.
        fuelflow (openap.FuelFlow): OpenAP fuel flow model.
        m_start (float): Initial mass [kg]

    Returns:
        tuple: fuel flow [kg/s], fuel used [kg], mass profile [kg]
    """
    dt = df.timestamp.diff().dt.total_seconds().bfill().values
    mass_current = m_start
    phase_map = {
        "GROUND": None,
        "CLIMB": fuelflow.nominal,
        "DESCENT": fuelflow.idle,
        "LEVEL": fuelflow.enroute,
        "CRUISE": fuelflow.enroute,
        "NA": None,
    }

    ff_lst = []
    fuel_lst = []
    mass_lst = []

    for row, step_dt in zip(df.itertuples(index=False), dt):
        ff_method = phase_map.get(row.phase)
        if step_dt == 0 or not ff_method:
            ff = 0.0
        else:
            ff = ff_method(
                mass=mass_current,
                tas=row.groundspeed,
                alt=row.altitude,
                vs=row.vertical_rate,
            )[0][0]

        ff = np.nan_to_num(ff, nan=0.0, posinf=0.0, neginf=0.0)
        fuel = ff * step_dt
        mass_current -= fuel

        ff_lst.append(ff)
        fuel_lst.append(fuel)
        mass_lst.append(mass_current)

    return np.array(ff_lst), np.array(fuel_lst), np.array(mass_lst)


def _fuel_flow_vectorised(
    df: pd.DataFrame, fuelflow: openap.FuelFlow, m_init: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Perform two-pass fuel flow calculation with initial mass guess.

    Args:
        df (pd.DataFrame): Flight data.
        fuelflow (openap.FuelFlow): OpenAP fuel flow model.
        m_init (float): Initial aircraft mass [kg].

    Returns:
        tuple: fuel flow [kg/s], fuel used [kg], final mass profile [kg]
    """
    n = len(df)
    mass_0 = np.full(n, m_init)
    dt = df.timestamp.diff().dt.total_seconds().bfill()

    phase_map = {
        "GROUND": None,
        "CLIMB": fuelflow.nominal,
        "DESCENT": fuelflow.idle,
        "LEVEL": fuelflow.enroute,
        "CRUISE": fuelflow.enroute,
        "NA": None,
    }

    ff_1 = _fuel_flow_vectorised_pass(df, phase_map, mass_0)
    mass = mass_0 - np.cumsum(ff_1 * dt)
    ff_2 = _fuel_flow_vectorised_pass(df, phase_map, mass)
    fuel = ff_2 * dt

    return np.array(ff_2), np.array(fuel), np.array(mass)


def _fuel_flow_vectorised_pass(
    df: pd.DataFrame, phase_map: dict, mass: np.ndarray
) -> np.ndarray:
    """Do a fuel flow calculation pass depending on the phase.

    Args:
        df (pd.DataFrame): Flight data.
        phase_map (dict): Dictionary mapping phases to fuelflow methods.
        mass (np.ndarray): mass [kg]

    Returns:
        np.ndarray: fuel flow [kg/s]
    """
    ff = np.zeros(len(df))
    for phase, method in phase_map.items():
        if method is None:
            continue
        p_idx = df["phase"] == phase
        if not np.any(p_idx):
            continue
        ff[p_idx] = method(
            mass=mass[p_idx],
            tas=df["groundspeed"].values[p_idx],
            alt=df["altitude"].values[p_idx],
            vs=df["vertical_rate"].values[p_idx],
        ).flatten()
    return np.nan_to_num(ff)
