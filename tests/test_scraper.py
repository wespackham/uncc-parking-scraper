import json
from unittest.mock import patch, MagicMock
import pytest
import requests

from src.scraper import scrape_and_store


def _make_response(lines):
    """Create a mock response whose iter_lines yields the given strings."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


SAMPLE_DATA = [
    {"lotCode": "A", "percentAvailable": 0.75},
    {"lotCode": "B", "percentAvailable": 0.30},
]


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_parses_and_inserts_snapshot(mock_get, mock_supabase):
    mock_get.return_value = _make_response([
        "",
        "data:" + json.dumps(SAMPLE_DATA),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    mock_supabase.table.assert_called_once_with("parking_data")
    inserted = mock_table.insert.call_args[0][0]
    assert inserted == {"data": {"A": 0.75, "B": 0.30}}
    mock_table.execute.assert_called_once()


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_skips_empty_and_non_data_lines(mock_get, mock_supabase):
    mock_get.return_value = _make_response([
        "",
        "event: update",
        "data:" + json.dumps(SAMPLE_DATA),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    mock_table.insert.assert_called_once()


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_skips_lots_missing_fields(mock_get, mock_supabase):
    data = [
        {"lotCode": "A", "percentAvailable": 0.5},
        {"lotCode": "B"},                          # missing percentAvailable
        {"percentAvailable": 0.9},                  # missing lotCode
        {},                                         # missing both
    ]
    mock_get.return_value = _make_response([
        "data:" + json.dumps(data),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    inserted = mock_table.insert.call_args[0][0]
    assert inserted == {"data": {"A": 0.5}}


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_no_insert_when_snapshot_empty(mock_get, mock_supabase):
    data = [{"noLotCode": True}]
    mock_get.return_value = _make_response([
        "data:" + json.dumps(data),
    ])

    scrape_and_store()

    mock_supabase.table.assert_not_called()


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_handles_network_error(mock_get, mock_supabase):
    mock_get.side_effect = requests.RequestException("Connection refused")

    scrape_and_store()  # should not raise

    mock_supabase.table.assert_not_called()


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_handles_malformed_json(mock_get, mock_supabase):
    mock_get.return_value = _make_response([
        "data: {not valid json",
    ])

    scrape_and_store()  # should not raise

    mock_supabase.table.assert_not_called()


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_only_processes_first_data_line(mock_get, mock_supabase):
    """The scraper returns after the first data: line it processes."""
    data1 = [{"lotCode": "A", "percentAvailable": 0.5}]
    data2 = [{"lotCode": "B", "percentAvailable": 0.9}]
    mock_get.return_value = _make_response([
        "data:" + json.dumps(data1),
        "data:" + json.dumps(data2),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    # Should only insert once (first data line), then return
    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted == {"data": {"A": 0.5}}
