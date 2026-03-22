from unittest.mock import patch, MagicMock
from src.daily_report import send_daily_report


def _mock_supabase(count):
    mock_result = MagicMock()
    mock_result.count = count
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = mock_result
    return mock_chain


@patch("src.daily_report.send_discord")
@patch("src.daily_report.supabase")
def test_full_count_sends_success(mock_supabase, mock_discord):
    mock_supabase.table.return_value = _mock_supabase(288)
    send_daily_report()
    mock_discord.assert_called_once()
    assert "✅" in mock_discord.call_args[0][0]
    assert "288/288" in mock_discord.call_args[0][0]


@patch("src.daily_report.send_discord")
@patch("src.daily_report.supabase")
def test_partial_count_sends_warning(mock_supabase, mock_discord):
    mock_supabase.table.return_value = _mock_supabase(250)
    send_daily_report()
    mock_discord.assert_called_once()
    assert "⚠️" in mock_discord.call_args[0][0]
    assert "250/288" in mock_discord.call_args[0][0]


@patch("src.daily_report.send_discord")
@patch("src.daily_report.supabase")
def test_zero_count_sends_alert(mock_supabase, mock_discord):
    mock_supabase.table.return_value = _mock_supabase(0)
    send_daily_report()
    mock_discord.assert_called_once()
    assert "🚨" in mock_discord.call_args[0][0]
