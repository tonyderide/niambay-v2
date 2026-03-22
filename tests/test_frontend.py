from pathlib import Path


def test_frontend_files_exist():
    base = Path("C:/niambay-v2/frontend")
    assert (base / "index.html").exists()
    assert (base / "css" / "style.css").exists()
    assert (base / "js" / "app.js").exists()
    assert (base / "js" / "ws.js").exists()
