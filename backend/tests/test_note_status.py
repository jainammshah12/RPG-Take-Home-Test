from unittest.mock import patch

from src.parsing.note_status import apply_note_statuses


def test_apply_note_statuses_uses_groq_when_available():
    rows = [
        {
            "note_type": "todo",
            "note_text": "[todo] greenloop still hasn't paid invoice 2",
            "status_raw": "Unknown",
        },
        {
            "note_type": "done",
            "note_text": "[done] adobe refund came through (~$40)",
            "status_raw": "Unknown",
        },
    ]
    mock_results = {"results": [{"id": 0, "status": "Pending"}, {"id": 1, "status": "Refunded"}]}

    with patch("src.parsing.note_status.groq_available", return_value=True):
        with patch("src.parsing.note_status.groq_chat_json", return_value=mock_results):
            apply_note_statuses(rows)

    assert rows[0]["status_raw"] == "Pending"
    assert rows[1]["status_raw"] == "Refunded"


def test_apply_note_statuses_fallback_without_groq():
    rows = [
        {
            "note_type": "todo",
            "note_text": "[todo] client still outstanding",
            "status_raw": "Unknown",
        },
    ]
    with patch("src.parsing.note_status.groq_available", return_value=False):
        apply_note_statuses(rows)
    assert rows[0]["status_raw"] == "Pending"
