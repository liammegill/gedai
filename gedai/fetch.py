"""
Functions that fetch ADS-B data and metadata.
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"

# imports
import requests


def fetch_raw_data(source: str, base_url: str, icao: str):
    """Fetch ADS-B data from a given source.

    Args:
        source (str): Source of the ADS-B data (e.g., "adsb_exchange").
        base_url (str): Base URL to fetch data from.
        icao (str): ICAO identifier of the aircraft.

    Returns:
        tuple[dict, dict]: A tuple containing the full data and extracted
            metadata.

    Raises:
        ValueError: If the source is unknown or unsupported.
    """
    if source == "adsb_exchange":
        base_url = f"{base_url}{icao[-2:]}/"
        return _fetch_adsb_exchange(base_url, icao)
    if source == "bjets":
        return _fetch_adsb_exchange(base_url, icao)
    raise ValueError(f"Unsupported ADS-B source: {source}")


def _fetch_adsb_exchange(base_url: str, icao: str):
    """Fetch JSON data from ADS-B Exchange.

    Args:
        base_url (str): Base URL for the ADS-B Exchange trace files.
        icao (str): ICAO hex code of the aircraft.

    Returns:
        tuple[dict, dict]: A tuple of full JSON data and its metadata.
    """
    url = f"{base_url}trace_full_{icao}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"Request failed: {err}")
        return None, None

    try:
        data = response.json()
    except ValueError as e:
        print(f"Invalid JSON: {e}")
        return None, None

    metadata = {k: v for k, v in data.items() if k != "trace"}
    return data, metadata
