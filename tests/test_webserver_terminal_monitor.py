import json

import pytest

from app.controllers import webserver


@pytest.fixture
def client():
    webserver.app.config.update(TESTING=True)
    with webserver.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def terminal_sandbox(tmp_path, monkeypatch):
    base_dir = tmp_path
    logs_dir = base_dir / "results" / "logs"
    logs_dir.mkdir(parents=True)
    cache_dir = base_dir / "results" / "cache"
    cache_dir.mkdir(parents=True)
    extra_logs_dir = base_dir / "logs"
    extra_logs_dir.mkdir(parents=True)

    monkeypatch.setattr(webserver, "BASE_DIR", base_dir)
    monkeypatch.setattr(
        webserver,
        "TERMINAL_MONITOR_DIRS",
        [logs_dir, extra_logs_dir, cache_dir],
    )

    return {
        "base": base_dir,
        "logs": logs_dir,
        "cache": cache_dir,
        "extra_logs": extra_logs_dir,
    }


def test_terminal_page_route_returns_html(client):
    response = client.get("/terminal")

    assert response.status_code == 200
    assert b"Terminal Output Monitor" in response.data


def test_api_terminal_files_returns_discovered_files(client, terminal_sandbox):
    (terminal_sandbox["logs"] / "job.log").write_text("line\n", encoding="utf-8")
    (terminal_sandbox["cache"] / "progress.json").write_text('{"ok": true}\n', encoding="utf-8")

    response = client.get("/api/terminal/files")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload is not None
    assert payload["files"] == [
        "results/cache/progress.json",
        "results/logs/job.log",
    ]


def test_api_terminal_tail_returns_lines_and_position(client, terminal_sandbox):
    log_file = terminal_sandbox["logs"] / "import.log"
    log_file.write_text("a\nb\nc\n", encoding="utf-8")

    response = client.get("/api/terminal/tail?file=results/logs/import.log&lines=2")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload is not None
    assert payload["file"] == "results/logs/import.log"
    assert payload["lines"] == ["b", "c"]
    assert payload["position"] == log_file.stat().st_size


def test_api_terminal_tail_rejects_invalid_path(client, terminal_sandbox):
    (terminal_sandbox["base"] / "secret.log").write_text("hidden\n", encoding="utf-8")

    response = client.get("/api/terminal/tail?file=../secret.log")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload is not None
    assert payload["error"] == "invalid file path"


def test_api_terminal_stream_rejects_invalid_path(client):
    response = client.get("/api/terminal/stream?file=../secret.log")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload is not None
    assert payload["error"] == "invalid file path"


def test_api_terminal_stream_returns_data_event(client, terminal_sandbox):
    log_file = terminal_sandbox["logs"] / "live.log"
    log_file.write_text("tick-1\ntick-2\n", encoding="utf-8")

    response = client.get("/api/terminal/stream?file=results/logs/live.log&position=0", buffered=False)
    first_event = next(response.response).decode("utf-8")
    response.close()

    assert response.status_code == 200
    assert first_event.startswith("data: ")

    payload_line = first_event.splitlines()[0]
    payload = json.loads(payload_line[len("data: ") :])
    assert payload["text"] == "tick-1\ntick-2\n"
    assert payload["position"] == log_file.stat().st_size
