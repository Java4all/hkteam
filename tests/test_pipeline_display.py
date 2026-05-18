from crisis.ui.pipeline_display import SPINNER_FRAMES, format_pipeline_progress


def test_progress_shows_spinner_when_active():
    stages = [
        {"id": "intake", "label": "Classify", "status": "complete"},
        {"id": "smart_route", "label": "Route", "status": "complete"},
        {"id": "run_specialists", "label": "Specialists", "status": "running"},
    ]
    text = format_pipeline_progress(stages, frame=1, active=True)
    assert "Progress" in text
    assert "crisis-progress-track" in text
    assert "crisis-progress-fill" in text
    assert any(c in text for c in ("◐", "◓", "◑", "◒", "◉"))


def test_progress_complete_banner():
    stages = [
        {"id": "intake", "label": "Classify", "status": "complete"},
        {"id": "aggregate", "label": "Briefing", "status": "complete"},
    ]
    text = format_pipeline_progress(stages, active=False)
    assert "✅" in text
    assert "Ready for operator review" in text
