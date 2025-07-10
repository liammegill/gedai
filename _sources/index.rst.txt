GEDAI Documentation
===================

Welcome to GEDAI /ˈdʒɛdaɪ/!

No, it's got nothing to do with space wizards or artificial intelligence.
It's just the most interesting name that we could come up with at short notice.

GEDAI (Generating Emission Datasets from Aircraft Inventories) is an add-on for the open-source response model `OpenAirClim <https://github.com/dlr-pa/oac>`_.
The package will eventually allow its users to:

- Create OpenAirClim-compatible emission inventories from ADS-B data (e.g. from OpenSky, ADS-B Exchange, Flightradar24);
- Generate OpenAirClim-compatible emission inventories from city pairs and aircraft types using `OpenAP <https://openap.dev/>`_'s Trajectory Optimiser;
- Create air traffic scenarios for normalisation and scaling of emission inventories
- Convert emission inventories between different formats (e.g. `.csv` to `.nc`)

The source code can be found on `GitHub <https://github.com/liammegill/gedai>`_.
If you find a bug, have a suggestion or think of a new feature, please use GitHub's issues.

Contents
========

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   api_ref
