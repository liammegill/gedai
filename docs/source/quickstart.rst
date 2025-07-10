Getting started
===============

Here we walk you through how to use this package.

.. jupyter-execute::

    import pandas as pd
    import openap
    from traffic.core import Flight
    import gedai

The first step is to load the raw ADS-B data.
For this example, we are going to follow the DLR's HALO (D-ADLR) Gulfstream 5 research aircraft.
The HALO has the unique ICAO transponder hex `3c5192`.
We will use the private-jets database compiled by `Gössling et al. (2024) <https://doi.org/10.1038/s43247-024-01775-z>`_  on 06/08/2022.

.. jupyter-execute::

    icao = "3c5192"
    base_url = "https://private-jets.fra1.digitaloceanspaces.com/globe_history/2022-08-06/"
    source = "adsb_exchange"
    data, metadata = gedai.fetch_raw_data("bjets", base_url, icao)

Fetching was successful!

.. jupyter-execute::

    ac_type = "GLF6"
    ac = openap.prop.aircraft(ac_type)
    df = gedai.create_dataframe(data, metadata, source)
    f = Flight(df)


Now let's plot the flight.


.. jupyter-execute::

    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.plot(f.data.longitude, f.data.latitude, "r", transform=ccrs.Geodetic())
    ax.coastlines()
