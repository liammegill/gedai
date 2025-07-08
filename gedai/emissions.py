"""
Functions to calculate emissions.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"

import openap
import numpy as np
import pandas as pd

from .core import assign_to_flight


# emission indices
EI_CO2 = 3.16  # Lee et al., 2010, Table 1, doi:10.1016/j.atmosenv.2009.06.005
EI_H2O = 1.24  # Lee et al., 2010, Table 1, doi:10.1016/j.atmosenv.2009.06.005


@assign_to_flight
def calc_emissions(
    df: pd.DataFrame, ac: dict, eng: str = None, **kwargs
) -> pd.DataFrame:
    """
    Calculate emission flows [kg/s] of CO2, H2O and NOx.

    Args:
        df (pd.DataFrame): Flight data.
        ac (dict): OpenAP aircraft dictionary
        eng (str, optional): Engine identifier, (e.g. "AE3007A1E").
            Defaults to None, at which point the default engine is used.

    Useful kwargs:
        nox_method (str): NOx calculation method, one of "dlr" or "boeing".

    Returns:
        pd.DataFrame: Flight data with new columns "co2flow", "h2oflow" and
            "noxflow".
    """

    # get aircraft and engine properties
    n_eng = float(ac["engine"]["number"])  # ensure division works
    if eng is None:
        eng = ac["engine"]["default"]

    # calculate emissions
    co2flow = calc_co2(df["fuelflow"])
    h2oflow = calc_h2o(df["fuelflow"])
    noxflow = calc_nox(
        df["fuelflow"], df["groundspeed"], df["altitude"], eng, n_eng, **kwargs
    )

    return df.assign(co2flow=co2flow, h2oflow=h2oflow, noxflow=noxflow)


def calc_co2(ff):
    """Calculate CO2 emission flow [kg/s].

    Args:
        ff (float | np.ndarray): Fuel flow [kg/s]

    Returns:
        float | np.ndarray: CO2 emission flow [kg/s]
    """
    return ff * EI_CO2


def calc_h2o(ff):
    """Calculate H2O emission flow [kg/s].

    Args:
        ff (float | np.ndarray): Fuel flow [kg/s]

    Returns:
        float | np.ndarray: H2O emission flow [kg/s]
    """
    return ff * EI_H2O


def calc_nox(
    ff: float | np.ndarray,
    tas: float | np.ndarray,
    alt: float | np.ndarray,
    eng: str,
    n_eng: int,
    nox_method="dlr",
):
    """Calculate NOx emissions.

    Args:
        ff (float | np.ndarray): Fuel flow [kg/s]
        tas (float | np.ndarray): Airspeed [kt]
        alt (float | np.ndarray): Altitude [ft]
        eng (str): Engine identifier (e.g. "AE3007A1E")
        n_eng (int): Number of engines
        nox_method (str, optional): NOx calculation method, one of "dlr" or
            "boeing". Defaults to "dlr".

    Raises:
        ValueError: If unknown NOx method.

    Returns:
        float | np.ndarray: NOx emissions [kg/s]
    """

    # get engine information
    engine = openap.prop.engine(eng)
    ff_per_eng = np.divide(ff, n_eng)

    # select NOx method
    if nox_method == "dlr":
        einox = _dlr_method(ff_per_eng, tas, alt, engine)
        return ff * einox
    if nox_method == "boeing":
        einox = _boeing_method(ff_per_eng, tas, alt, engine)
        return ff * einox

    raise ValueError("Unknown nox_method.")


def _dlr_method(
    ff_per_eng: float | np.ndarray,
    tas: float | np.ndarray,
    alt: float | np.ndarray,
    engine: dict,
) -> float | np.ndarray:
    """Use the DLR Fuel Flow Method to calculate EINOx.

    Args:
        ff_per_eng (float | np.ndarray): Fuel flow [kg/s] per engine.
        tas (float | np.ndarray): Airpeed [kt]
        alt (float | np.ndarray): Altitude [ft]
        engine (dict): OpenAP engine object.

    Returns:
        float | np.ndarray: EINOx [kg/kg]
    """

    # pressure and temperature
    mach = openap.aero.tas2mach(tas * openap.aero.kts, alt * openap.aero.ft)
    p_amb = openap.aero.pressure(alt * openap.aero.ft)
    t_amb = openap.aero.temperature(alt * openap.aero.ft)

    # reference fuel flow
    delta = p_amb * (1 + 0.2 * mach**2) ** 3.5 / 101325.0
    theta = t_amb * (1 + 0.2 * mach**2) / 288.15
    w_ref = ff_per_eng / (delta * np.sqrt(theta))

    # calculate EINOx in reference conditions using polynomial
    ff_lst = [engine[f"ff_{x}"] for x in ["idl", "app", "co", "to"]]
    einox_lst = [engine[f"ei_nox_{x}"] for x in ["idl", "app", "co", "to"]]
    coeffs = np.polyfit(ff_lst, einox_lst, 2)
    einox_ref = np.polyval(coeffs, w_ref)

    # scale back to actual conditions
    omega = 1e-3 * np.exp(-0.0001426 * (alt - 12900.0))
    h = -19.0 * (omega - 0.00634)
    einox = einox_ref * delta**0.4 * theta**3 * np.exp(h)

    return einox * 1e-3  # convert to kg/kg


def _boeing_method(
    ff_per_eng: float | np.ndarray,
    tas: float | np.ndarray,
    alt: float | np.ndarray,
    engine: dict,
) -> float | np.ndarray:
    """Use the Boeing Fuel Flow Method to calculate EINOx.

    Args:
        ff_per_eng (float | np.ndarray): Fuel flow [kg/s] per engine.
        tas (float | np.ndarray): Airpeed [kt]
        alt (float | np.ndarray): Altitude [ft]
        engine (dict): OpenAP engine object.

    Returns:
        float | np.ndarray: EINOx [kg/kg]
    """

    # note that in the Boeing method, delta and theta are based on the ambient
    # temperature and pressure, not the total
    mach = openap.aero.tas2mach(tas * openap.aero.kts, alt * openap.aero.ft)
    p_amb = openap.aero.pressure(alt * openap.aero.ft)
    t_amb = openap.aero.temperature(alt * openap.aero.ft)
    delta = p_amb / 101325.0
    theta = t_amb / 288.15

    # calculate reference fuel flow
    w_ff = ff_per_eng / delta * theta**3.8 * np.exp(0.2 * mach**2)

    # calculate EINOx in reference conditions using piecewise linear fits
    # on log-log plots; correct for engine installation (r)
    log_ff = np.log(
        [
            engine[f"ff_{x}"] * r
            for x, r in zip(
                ["idl", "app", "co", "to"],
                [1.100, 1.020, 1.013, 1.010],
            )
        ]
    )
    log_einox = np.log(
        [
            np.maximum(engine[f"ei_nox_{x}"], 1e-6)  # potential zeros for log
            for x in ["idl", "app", "co", "to"]
        ]
    )
    log_einox_ref = np.interp(np.log(w_ff), log_ff, log_einox)
    einox_ref = np.exp(log_einox_ref)

    # correct back to actual conditions
    # assuming ISA, then phi becomes 0 and a lot cancels out
    phi = 0.0
    tau = 373.16 / t_amb
    beta = (
        7.90298 * (1 - tau)
        + 3.00571
        + 5.02808 * np.log(tau)
        + 1.3816e-7 * (1 - 10 ** (11.344 * (1 - 1 / tau)))
        + 8.1328e-3 * (10 ** (3.49149 * (1 - tau)) - 1)
    )
    p_v = 0.014504 * 10**beta
    omega = (0.62197058 * phi * p_v) / (p_amb - phi * p_v)
    h = -19.0 * (omega - 0.00634)
    einox = einox_ref * np.sqrt(delta**1.02 / theta**3.3) * np.exp(h)

    return einox * 1e-3  # convert to kg/kg
