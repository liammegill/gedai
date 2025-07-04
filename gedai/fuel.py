"""
Functions to calculate fuel use.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"

# imports
import openap
# from openap.addon import bada3  # waiting for PR #59 at OpenAP
import pandas as pd
import numpy as np

from .core import assign_to_flight


@assign_to_flight
def compute_fuel_flow_iterative(
    df: pd.DataFrame,
    fuelflow: openap.FuelFlow,
    starting_mass: float
) -> pd.DataFrame:
    """Calculate fuel flow.

    Args:
        df (pd.DataFrame): Flight data.
        fuelflow (openap.FuelFlow): Instance of the OpenAP FuelFlow class.
        starting_mass (float): Initial mass of the aircraft [kg]

    Returns:
        pd.DataFrame: DataFrame modified in place with new columns "fuel_flow"
            [kg/s] and "fuel" [kg].
    """
    # pre-conditions
    # test starting_mass > 0
    mass_current = starting_mass
    dt = df.timestamp.diff().dt.total_seconds().bfill().values

    # map phases to fuel flow methods
    phase_map = {
        "GROUND": None,
        "CLIMB": fuelflow.nominal,
        "DESCENT": fuelflow.idle,
        "LEVEL": fuelflow.enroute,
        "CRUISE": fuelflow.enroute,
        "NA": None,
    }

    # calculate fuel flow and fuel per timestep
    ff_lst = []
    fuel_lst = []
    for row, step_dt in zip(df.itertuples(index=False), dt):
        ff_method = phase_map.get(row.phase)
        if row.dt == 0 or not ff_method:
            ff = 0.0
        else:
            ff = ff_method(
                mass=mass_current,
                tas=row.groundspeed,
                alt=row.altitude,
                vs=row.vertical_rate,
            )[0][0]
        # TODO: log any fuel flow issues (e.g. negative values)
        # protect against NaNs
        ff = np.nan_to_num(ff, nan=0.0, posinf=0.0, neginf=0.0)
        fuel = ff * step_dt
        mass_current -= fuel
        ff_lst.append(ff)
        fuel_lst.append(fuel)

    return df.assign(fuelflow=ff_lst, fuel=fuel_lst, dt=dt)


@assign_to_flight
def compute_fuel_flow_vectorised(
    df: pd.DataFrame,
    fuelflow: openap.FuelFlow,
    starting_mass: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate fuel flow using a vectorised approach. This method uses two
    passes: the first pass calculates the fuel flow assuming the mass is
    constant (starting_mass). The mass is then corrected using this fuel flow.
    The fuel flow and fuel use is calculated in a second pass with the
    corrected mass. Note that this is an approximation, but it is also
    around 100 times faster.

    Args:
        df (pd.DataFrame): Flight data.
        fuelflow (openap.FuelFlow): Instance of the OpenAP FuelFlow class.
        starting_mass (float): Initial mass of the aircraft [kg]

    Returns:
        tuple[np.ndarray, np.ndarray]: Fuel flow [kg/s] and fuel [kg]
    """

    # map phases to fuel flow methods
    phase_map = {
        "GROUND": None,
        "CLIMB": fuelflow.nominal,
        "DESCENT": fuelflow.idle,
        "LEVEL": fuelflow.enroute,
        "CRUISE": fuelflow.enroute,
        "NA": None,
    }

    # first pass: using reference mass
    n = len(df)
    mass_0 = np.full(n, starting_mass)
    dt = df.timestamp.diff().dt.total_seconds().bfill()
    ff_1 = _fuel_flow_pass(df, phase_map, mass_0)
    mass = mass_0 - np.cumsum(ff_1 * dt)

    # second pass with corrected mass
    ff_2 = _fuel_flow_pass(df, phase_map, mass)
    fuel = ff_2 * dt

    return df.assign(fuelflow=ff_2, fuel=fuel, dt=dt)


def _fuel_flow_pass(
    df: pd.DataFrame,
    phase_map: dict,
    mass: np.ndarray
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


# Waiting for PR #59 at OpenAP

# def calc_starting_mass(method: str, **kwargs) -> float:
#     """Calculate aircraft starting mass.

#     Args:
#         method (str): Method by which to calculate starting mass. Currently
#             implemented is 'BADA3'.

#     Raises:
#         ValueError: Missing kwargs for each method.
#         ValueError: Invalid of unsupported method.

#     Returns:
#         float: Starting aircraft mass [kg]
#     """

#     if method == "BADA3":
#         req_kwargs = ["ac_type", "bada_version", "bada_path"]
#         missing = [kw for kw in req_kwargs if kw not in kwargs]
#         if missing:
#             raise ValueError(f"Missing kwargs: {missing}")
#         return _calc_starting_mass_bada3(**kwargs)
#     raise ValueError("Invalid or unsupported method. Supported are: ['BADA3']")


# def _calc_starting_mass_bada3(
#     ac_type: str, bada_version: str, bada_path: str = None
# ) -> float:
#     """Calculate aircraft starting mass using BADA3.

#     Args:
#         ac_type (str): ICAO aircraft type designator (e.g. G280)
#         bada_version (str): Identifier of BADA3 version. Required if
#             `bada_path=None`, else has no functionality but must be provided.
#         bada_path (str, optional): Path to BADA3 models. If None, data is taken
#             from `pyBADA/aircraft/BADA3/{badaVersion}/`.

#     Returns:
#         float: Starting aircraft mass [kg]
#     """
#     # TODO: maybe there's a better way to estimate initial mass
#     # maybe we should ensure that MREF - total fuel use doesn't drop below OEW
#     acmod = bada3.load_bada3(ac_type, bada_version, bada_path)
#     starting_mass = acmod.MTOW * 0.9

#     return starting_mass
