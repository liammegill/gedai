# GEDAI


![Python](https://img.shields.io/badge/language-Python-blue)
[![GitHub issues](https://img.shields.io/github/issues/liammegill/gedai)](#)
[![GitHub last commit](https://img.shields.io/github/last-commit/liammegill/gedai)](#)
![Tests](https://github.com/liammegill/gedai/actions/workflows/install_and_test.yml/badge.svg)
<!-- [![GitHub release](https://img.shields.io/github/v/release/liammegill/gedai)](#) -->
<!--[![GitHub release date](https://img.shields.io/github/release-date/liammegill/gedai)](#) -->


## Description

GEDAI (Generating Emission Datasets from Aircraft Inventories) is an add-on for the open-source response model [OpenAirClim](https://github.com/dlr-pa/oac).
It uses ADS-B trajectory data or sets of city pairs to create OpenAirClim-compatible emission inventories.
It also includes a number of useful tools for converting, scaling or otherwise modifying existing emission inventories.


## Installation

First, clone the repository using git:

```
git clone https://github.com/liammegill/gedai.git
```

Then, install the dependencies using conda.

```
conda env create -f environment.yaml
```

## Contact
Liam Megill - liam.megill@dlr.de


## License
Distributed under the Apache License 2.0, which can be found [here](LICENSE).
