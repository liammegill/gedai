"""
Provides tests for fetch.py
"""

__author__ = "Liam Megill"
__email__ = "liam.megill@dlr.de"
__license__ = "Apache License 2.0"

from unittest.mock import patch, Mock
import pytest
from requests.exceptions import RequestException
import gedai


class TestFetchRawData:
    """Tests function fetch_raw_data(source, base_url, icao)."""

    def test_valid_adsb_exchange_request_success(self):
        """
        Test successful data fetch and metadata extraction from ADS-B
        Exchange.
        """
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "trace": [[1, 2, 3]],
            "icao": "abc123",
            "r": "N123AB",
            "t": "XYZ",
        }

        with patch(
            "gedai.fetch.requests.get", return_value=mock_response
        ) as mock_get:
            base_url = "https://example.com/"
            icao = "abc123"
            data, metadata = gedai.fetch_raw_data(
                "adsb_exchange", base_url, icao
            )

            assert data is not None
            assert metadata == {"icao": "abc123", "r": "N123AB", "t": "XYZ"}
            mock_get.assert_called_once_with(
                "https://example.com/23/trace_full_abc123.json", timeout=10
            )

    def test_request_fails_returns_none(self):
        """Test that request failure returns (None, None)."""
        with patch("gedai.fetch.requests.get") as mock_get:
            mock_get.side_effect = RequestException("Connection error")

            data, metadata = gedai.fetch_raw_data(
                "adsb_exchange", "https://example.com/", "def456"
            )
            assert data is None
            assert metadata is None

    def test_invalid_json_returns_none(self):
        """Test that invalid JSON returns (None, None)."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("gedai.fetch.requests.get", return_value=mock_response):
            data, metadata = gedai.fetch_raw_data(
                "adsb_exchange", "https://example.com/", "ghi789"
            )
            assert data is None
            assert metadata is None

    def test_unsupported_source_raises_error(self):
        """Test that unsupported sources raise a ValueError."""
        with pytest.raises(
            ValueError, match="Unsupported ADS-B source: opensky"
        ):
            gedai.fetch_raw_data("opensky", "https://example.com/", "jkl000")
