import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.scraper import flush_buffered_snapshots, scrape_and_store


def _make_response(lines):
    """Create a mock response whose iter_lines yields the given strings."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


SAMPLE_DATA = [
    {"lotCode": "A", "percentAvailable": 0.75},
    {"lotCode": "B", "percentAvailable": 0.30},
]


@pytest.fixture
def buffer_file(tmp_path, monkeypatch):
    path = tmp_path / "pending_snapshots.jsonl"
    monkeypatch.setattr("src.scraper.BUFFER_FILE", path)
    monkeypatch.setattr("src.scraper.MAX_BUFFER_FLUSH", 500)
    return path


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_parses_buffers_and_inserts_snapshot(mock_get, mock_supabase, buffer_file):
    mock_get.return_value = _make_response([
        "",
        "data:" + json.dumps(SAMPLE_DATA),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    mock_supabase.table.assert_called_with("parking_data")
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["data"] == {"A": 0.75, "B": 0.30}
    assert "created_at" in inserted
    mock_table.execute.assert_called_once()
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_skips_empty_and_non_data_lines(mock_get, mock_supabase, buffer_file):
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
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_skips_lots_missing_fields(mock_get, mock_supabase, buffer_file):
    data = [
        {"lotCode": "A", "percentAvailable": 0.5},
        {"lotCode": "B"},
        {"percentAvailable": 0.9},
        {},
    ]
    mock_get.return_value = _make_response([
        "data:" + json.dumps(data),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    inserted = mock_table.insert.call_args[0][0]
    assert inserted["data"] == {"A": 0.5}
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_no_insert_when_snapshot_empty(mock_get, mock_supabase, buffer_file):
    data = [{"noLotCode": True}]
    mock_get.return_value = _make_response([
        "data:" + json.dumps(data),
    ])

    scrape_and_store()

    mock_supabase.table.assert_not_called()
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.send_discord")
@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_handles_network_error(mock_get, mock_supabase, mock_discord, buffer_file):
    mock_get.side_effect = requests.RequestException("Connection refused")

    scrape_and_store()

    mock_supabase.table.assert_not_called()
    mock_discord.assert_called_once()
    assert "network error" in mock_discord.call_args[0][0]
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.send_discord")
@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_handles_malformed_json(mock_get, mock_supabase, mock_discord, buffer_file):
    mock_get.return_value = _make_response([
        "data: {not valid json",
    ])

    scrape_and_store()

    mock_supabase.table.assert_not_called()
    mock_discord.assert_called_once()
    assert "JSON" in mock_discord.call_args[0][0]
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_only_processes_first_data_line(mock_get, mock_supabase, buffer_file):
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

    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["data"] == {"A": 0.5}
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.send_discord")
@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_failed_insert_stays_buffered_for_retry(mock_get, mock_supabase, mock_discord, buffer_file):
    mock_get.return_value = _make_response([
        "data:" + json.dumps(SAMPLE_DATA),
    ])
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.side_effect = RuntimeError("401 unauthorized")

    scrape_and_store()

    buffered = _read_jsonl(buffer_file)
    assert len(buffered) == 1
    assert buffered[0]["data"] == {"A": 0.75, "B": 0.30}
    mock_discord.assert_called_once()
    assert "buffered retry failed" in mock_discord.call_args[0][0]


@patch("src.scraper.supabase")
def test_flush_replays_buffered_snapshots_in_order(mock_supabase, buffer_file):
    older = {"created_at": "2026-04-26T00:00:00+00:00", "data": {"A": 0.10}}
    newer = {"created_at": "2026-04-26T00:05:00+00:00", "data": {"A": 0.20}}
    buffer_file.write_text(json.dumps(older) + "\n" + json.dumps(newer) + "\n")

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    inserted, remaining = flush_buffered_snapshots()

    assert inserted == 2
    assert remaining == 0
    assert [call.args[0] for call in mock_table.insert.call_args_list] == [older, newer]
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.supabase")
@patch("src.scraper.requests.get")
def test_next_successful_run_flushes_buffer_then_current(mock_get, mock_supabase, buffer_file):
    older = {"created_at": "2026-04-26T00:00:00+00:00", "data": {"A": 0.10}}
    buffer_file.write_text(json.dumps(older) + "\n")
    mock_get.return_value = _make_response([
        "data:" + json.dumps(SAMPLE_DATA),
    ])

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table

    scrape_and_store()

    inserted_records = [call.args[0] for call in mock_table.insert.call_args_list]
    assert inserted_records[0] == older
    assert inserted_records[1]["data"] == {"A": 0.75, "B": 0.30}
    assert inserted_records[1]["created_at"] != older["created_at"]
    assert _read_jsonl(buffer_file) == []


@patch("src.scraper.send_discord")
@patch("src.scraper.supabase")
def test_flush_keeps_remaining_records_after_failure(mock_supabase, mock_discord, buffer_file):
    first = {"created_at": "2026-04-26T00:00:00+00:00", "data": {"A": 0.10}}
    second = {"created_at": "2026-04-26T00:05:00+00:00", "data": {"A": 0.20}}
    buffer_file.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n")

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.side_effect = [None, RuntimeError("insert failed")]

    inserted, remaining = flush_buffered_snapshots()

    assert inserted == 1
    assert remaining == 1
    assert _read_jsonl(buffer_file) == [second]
    mock_discord.assert_called_once()
    assert "buffered retry failed" in mock_discord.call_args[0][0]
