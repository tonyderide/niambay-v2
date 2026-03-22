from daemon.llm.google import GoogleProvider


def test_google_has_vision():
    gp = GoogleProvider(api_key="test")
    assert hasattr(gp, 'analyze_image')
