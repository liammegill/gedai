"""
Provides tests for fuel.py
"""

import numpy as np
import pandas as pd
import pytest
from traffic.core import Flight

import gedai


# fixtures and mocks
# pylint: disable=redefined-outer-name


@pytest.fixture
def dummy_df():
    """Dummy flight data DataFrame."""
    timestamps = pd.date_range("2023-01-01", periods=5, freq="1min")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "phase": ["CLIMB", "CLIMB", "CRUISE", "DESCENT", "GROUND"],
            "groundspeed": [200, 220, 240, 180, 0],
            "altitude": [1000, 5000, 10000, 3000, 0],
            "vertical_rate": [1000, 800, 0, -1000, 0],
        }
    )


@pytest.fixture
def dummy_ff():
    """Dummy fuel flow class."""

    class _DummyFuelFlow:
        def nominal(self, mass, tas, alt, vs):
            """Nominal fuel flow."""
            return np.array([[0.5]]) * np.ones_like(mass).reshape(-1, 1)

        def idle(self, mass, tas, alt, vs):
            """Idle fuel flow."""
            return np.array([[0.2]]) * np.ones_like(mass).reshape(-1, 1)

        def enroute(self, mass, tas, alt, vs):
            """Enroute fuel flow."""
            return np.array([[0.3]]) * np.ones_like(mass).reshape(-1, 1)

    return _DummyFuelFlow()


@pytest.fixture
def dummy_ac():
    """Dummy aircraft dictionary."""
    return {"mtow": 60_000.0, "oew": 30_000.0}


# test classes


class TestFuelFlowInputHandling:
    """Tests input handling of fuel flow calculations."""

    def test_mass_as_fraction(self, dummy_df, dummy_ff, dummy_ac):
        """Tests mass input given as fraction between 0 and 1."""
        df = gedai.compute_fuel_flow(
            dummy_df, dummy_ff, 0.5, dummy_ac, vectorised=True
        )
        assert np.all(df["fuel"] >= 0)

    def test_invalid_mass_negative(self, dummy_df, dummy_ff, dummy_ac):
        """Tests invalid, negative input mass."""
        with pytest.raises(ValueError):
            gedai.compute_fuel_flow(dummy_df, dummy_ff, -1, dummy_ac)

    def test_invalid_mass_too_high(self, dummy_df, dummy_ff, dummy_ac):
        """Tests when input mass is higher than MTOW."""
        with pytest.raises(ValueError):
            gedai.compute_fuel_flow(dummy_df, dummy_ff, 70000, dummy_ac)

    def test_flight_object_input(self, dummy_df, dummy_ff, dummy_ac):
        """Tests that inputting a flight object also works."""
        flight = Flight(dummy_df)
        result = gedai.compute_fuel_flow(flight, dummy_ff, 0.9, dummy_ac)
        assert isinstance(result, Flight)
        assert "fuel" in result.data.columns
        assert "fuelflow" in result.data.columns


class TestFuelFlowIterative:
    """Tests iterative fuel flow calculation."""

    def test_iterative_fuel_is_positive(self, dummy_df, dummy_ff, dummy_ac):
        """Tests that all output fuel flows are positive for good run."""
        df = gedai.compute_fuel_flow(
            dummy_df, dummy_ff, 0.9, dummy_ac, vectorised=False
        )
        assert (df["fuel"] >= 0).all()


class TestFuelFlowVectorised:
    """Tests vectorised fuel flow calculation."""

    def test_vectorised_fuel_is_positive(self, dummy_df, dummy_ff, dummy_ac):
        """Tests that all output fuel flows are positive for good run."""
        df = gedai.compute_fuel_flow(
            dummy_df, dummy_ff, 0.9, dummy_ac, vectorised=True
        )
        assert (df["fuel"] >= 0).all()


class TestFuelFlowOutput:
    """Tests the output of the fuel flow calculation."""

    def test_output_columns_exist(self, dummy_df, dummy_ff, dummy_ac):
        """Tests whether expected output columns exist."""
        df = gedai.compute_fuel_flow(dummy_df, dummy_ff, 0.9, dummy_ac)
        assert set(["fuelflow", "fuel", "dt"]).issubset(df.columns)

    def test_output_lengths_match(self, dummy_df, dummy_ff, dummy_ac):
        """Tests whether expected output columns are of the right shape."""
        df = gedai.compute_fuel_flow(dummy_df, dummy_ff, 0.9, dummy_ac)
        assert len(df["fuelflow"]) == len(dummy_df)
        assert len(df["fuel"]) == len(dummy_df)

    def test_low_starting_mass(self, dummy_df, dummy_ff, dummy_ac):
        """Tests that the function defaults to MTOW after first pass."""
        df1 = gedai.compute_fuel_flow(
            dummy_df, dummy_ff, 0.1, dummy_ac, retry_with_mtow=True
        )
        df2 = gedai.compute_fuel_flow(
            dummy_df, dummy_ff, 0.2, dummy_ac, retry_with_mtow=True
        )
        np.testing.assert_allclose(df1["fuel"], df2["fuel"], rtol=1e-6)
        np.testing.assert_allclose(df1["fuelflow"], df2["fuelflow"], rtol=1e-6)

    def test_low_starting_mass_no_retry(self, dummy_df, dummy_ff, dummy_ac):
        """Tests that the function gives an error if final mass too low."""
        with pytest.raises(ValueError, match="Final mass .* below OEW"):
            gedai.compute_fuel_flow(
                dummy_df, dummy_ff, 0.1, dummy_ac, retry_with_mtow=False
            )
