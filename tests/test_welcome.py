from crisis.ui.welcome import format_welcome_message


def test_welcome_minimal_title_and_subtitle():
    html = format_welcome_message(include_help=False)
    assert "Smart City Crisis Management" in html
    assert "Emergency Operations Center — Incident Analysis Console" in html
    assert "ingests situation reports" not in html


def test_welcome_help_collapsed_by_default():
    html = format_welcome_message(include_help=True)
    assert '<details class="crisis-help">' in html
    assert "crisis-help-icon" in html
    assert " Help" in html
    assert "Submit an incident" in html
