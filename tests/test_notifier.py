from unittest.mock import patch, MagicMock
from src.notifier import send_discord


@patch("src.notifier.requests.post")
def test_sends_message(mock_post):
    send_discord("hello")
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"content": "hello"}


@patch("src.notifier.requests.post")
def test_silences_exceptions(mock_post):
    mock_post.side_effect = Exception("network down")
    send_discord("hello")  # should not raise
