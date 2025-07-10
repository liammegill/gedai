"""
Provides tests for preprocess.py
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"


import pandas as pd
import pytest
import gedai


class TestCreateDataframe:
    """Tests function create_dataframe(data, metadata, source, filters)."""

    @pytest.fixture
    def sample_data(self):
        """Fixture of sample ADS-B data."""
        return {
            "trace": [
                [0, 10.0, 20.0, 30000, 450, 90, 2, 0, 0, 0, 0, 0, 0, 0],
                [1, 10.1, 20.1, 31000, 455, 91, 0, 100, 0, 0, 0, 0, 0, 0],
            ]
        }

    @pytest.fixture
    def sample_metadata(self):
        """Fixture of sample ADS-B metadata."""
        return {
            "timestamp": 1620000000, "icao": "abcd12", "r": "N12345",
            "t": "B737"
        }

    def test_valid(self, sample_data, sample_metadata):
        """Tests valid input dataframe."""
        df = gedai.create_dataframe(
            sample_data, sample_metadata, "adsb_exchange"
        )
        assert isinstance(df, pd.DataFrame)
        assert not df.isnull().any().any()
        req_cols = ["timestamp", "icao24", "type", "registration"]
        for req_col in req_cols:
            assert req_col in df.columns, f"Missing column {req_col}"

    def test_invalid_data(self):
        """Tests empty/invalid input data."""
        with pytest.raises(ValueError, match="'trace'"):
            gedai.create_dataframe({}, {}, "adsb_exchange")

    def test_invalid_source(self, sample_data, sample_metadata):
        """Tests invalid ADS-B source."""
        with pytest.raises(ValueError, match="source"):
            gedai.create_dataframe(sample_data, sample_metadata, "opensky")


class TestStandardiseColumns:
    """Tests function standardise_columns(df, source)."""

    def test_invald_source(self):
        """Tests invalid ADS-B source."""
        df = pd.DataFrame([[0]*14])
        with pytest.raises(ValueError, match="source"):
            gedai.standardise_columns(df, "opensky")

    def test_wrong_input_shape(self):
        """Tests incorrect input shape."""
        df = pd.DataFrame([[0]*10])
        with pytest.raises(ValueError, match="columns"):
            gedai.standardise_columns(df, "adsb_exchange")


class TestAddMetadataColumns:
    """Tests function add_metadata_columns(df, metadata, source)."""

    def test_missing_keys(self):
        """Tests missing metadata keys."""
        metadata = {}
        df = pd.DataFrame([[0]*14])
        with pytest.raises(KeyError, match="keys"):
            gedai.add_metadata_columns(df, metadata, "adsb_exchange")
