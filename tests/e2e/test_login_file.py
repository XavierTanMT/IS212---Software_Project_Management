from pathlib import Path


def test_login_file_contains_form():
    repo_root = Path(__file__).resolve().parents[2]
    # Try login.html first, fall back to index.html
    candidates = [
        repo_root / "frontend_Xavier" / "login.html",
        repo_root / "frontend_Xavier" / "index.html",
        repo_root / "frontend_Xavier" / "index.htm",
    ]

    found = None
    for p in candidates:
        if p.exists():
            found = p
            break

    assert found is not None, f"No login/index file found in frontend_Xavier; checked: {candidates}"

    html = found.read_text(encoding="utf-8")

    # Basic heuristics: look for a form tag or a link to login
    assert "<form" in html.lower() or "login" in html.lower(), "login page does not appear to contain expected content"
