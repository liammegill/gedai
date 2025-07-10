"""
Provides tests for emissions.py
"""

import pytest
import numpy as np
import openap
import gedai


# fixtures
# pylint: disable=redefined-outer-name


@pytest.fixture
def dummy_engine():
    """Fixture for engine NOx values."""
    return {
        "ff_idl": 0.2,
        "ff_app": 0.5,
        "ff_co": 0.8,
        "ff_to": 1.0,
        "ei_nox_idl": 5.0,
        "ei_nox_app": 10.0,
        "ei_nox_co": 15.0,
        "ei_nox_to": 20.0,
    }


@pytest.fixture
def test_conditions():
    """Fixture for test conditions."""
    return {
        "ff": np.array([0.4, 0.6, 0.8]),
        "tas": np.array([250, 300, 340]),
        "alt": np.array([10000, 20000, 30000]),
    }


class TestCalcNOx:
    """Tests function calc_nox()."""

    def test_valid_dlr_method(
        self, test_conditions, dummy_engine, monkeypatch
    ):
        """Test valid DLR Fuel Flow Method calculation."""
        monkeypatch.setattr(openap.prop, "engine", lambda x: dummy_engine)
        ff, tas, alt = test_conditions.values()
        result = gedai.calc_nox(
            ff, tas, alt, "dummy_engine", 2, nox_method="dlr"
        )
        assert np.all(result >= 0), "NOx emissions must be non-negative"

    def test_valid_boeing_method(
        self, test_conditions, dummy_engine, monkeypatch
    ):
        """Test valid Boeing Fuel Flow Method calculation."""
        monkeypatch.setattr(openap.prop, "engine", lambda x: dummy_engine)
        ff, tas, alt = test_conditions.values()
        result = gedai.calc_nox(
            ff, tas, alt, "dummy_engine", 2, nox_method="boeing"
        )
        assert np.all(result >= 0), "NOx emissions must be non-negative"

    def test_invalid_method(self, test_conditions, monkeypatch):
        """Test invalid nox_method input."""
        monkeypatch.setattr(openap.prop, "engine", lambda x: dummy_engine)
        ff, tas, alt = test_conditions.values()
        with pytest.raises(ValueError, match="Unknown nox_method"):
            gedai.calc_nox(
                ff, tas, alt, "dummy_engine", 2, nox_method="unknown"
            )

    def test_negative_ff(self, dummy_engine, monkeypatch):
        """Test negative fuel flow input."""
        monkeypatch.setattr(openap.prop, "engine", lambda x: dummy_engine)
        with pytest.raises(ValueError, match="Fuel flow must be non-negative"):
            gedai.calc_nox(-0.5, 300, 10000, "dummy_engine", 2)

    def test_invalid_n_eng(self, dummy_engine, monkeypatch):
        """Test invalid number of engines."""
        monkeypatch.setattr(openap.prop, "engine", lambda x: dummy_engine)
        with pytest.raises(
            ValueError, match="n_eng must be a positive number."
        ):
            gedai.calc_nox(0.5, 300, 10000, "dummy_engine", 0)
