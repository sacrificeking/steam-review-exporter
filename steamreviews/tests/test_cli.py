import importlib.metadata as metadata

import pytest
import pydantic

from export_reviews import get_validated_config, main, parse_args, run_cli


def get_console_script_entrypoint() -> metadata.EntryPoint:
    entry_points = metadata.entry_points(group="console_scripts")
    for entry_point in entry_points:
        if entry_point.name == "steam-review-exporter":
            return entry_point
    pytest.fail("Installed console script entry point 'steam-review-exporter' was not found.")


def test_parse_args_accepts_non_interactive_config():
    args = parse_args(
        [
            "--app-id",
            "588650",
            "--language",
            "english",
            "--filter",
            "recent",
            "--min-len",
            "100",
            "--max-len",
            "500",
            "--output-dir",
            "exports",
        ]
    )

    assert args.app_id == 588650
    assert args.language == "english"
    assert args.filter_type == "recent"
    assert args.min_len == 100
    assert args.max_len == 500
    assert args.output_dir == "exports"


def test_parse_args_requires_app_id_and_language_for_cli_config():
    with pytest.raises(SystemExit):
        parse_args(["--app-id", "588650"])


def test_get_validated_config_from_args():
    args = parse_args(["--app-id", "588650", "--language", "GerMan", "--output-dir", "exports"])

    config = get_validated_config(args)

    assert config.app_id == 588650
    assert config.language == "german"
    assert config.filter_type == "all"
    assert config.output_dir == "exports"


def test_main_returns_success_and_does_not_prompt_again_in_non_interactive_mode(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr(
        "export_reviews.fetch_reviews",
        lambda app_id, language, filter_type, min_len, max_len: [{"review": "Nice", "author": {}}],
    )
    monkeypatch.setattr("export_reviews.process_reviews", lambda reviews, app_id: object())
    monkeypatch.setattr("export_reviews.save_to_excel", lambda *args, **kwargs: True)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail(f"Unexpected prompt: {prompt}"))

    assert main(["--app-id", "588650", "--language", "english"]) == 0


def test_main_returns_failure_when_no_reviews_are_found(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr("export_reviews.fetch_reviews", lambda *args, **kwargs: [])
    monkeypatch.setattr("export_reviews.process_reviews", lambda *args, **kwargs: pytest.fail("Unexpected processing"))
    monkeypatch.setattr("export_reviews.save_to_excel", lambda *args, **kwargs: pytest.fail("Unexpected export"))

    assert main(["--app-id", "588650", "--language", "english"]) == 1


def test_main_returns_failure_when_downloader_raises(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")

    def raise_download_error(*args, **kwargs):
        raise RuntimeError("download failed")

    monkeypatch.setattr("export_reviews.fetch_reviews", raise_download_error)

    assert main(["--app-id", "588650", "--language", "english"]) == 1


def test_main_returns_failure_when_export_raises(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr("export_reviews.fetch_reviews", lambda *args, **kwargs: [{"review": "Nice", "author": {}}])
    monkeypatch.setattr("export_reviews.process_reviews", lambda *args, **kwargs: object())

    def raise_export_error(*args, **kwargs):
        raise RuntimeError("export failed")

    monkeypatch.setattr("export_reviews.save_to_excel", raise_export_error)

    assert main(["--app-id", "588650", "--language", "english"]) == 1


def test_main_returns_failure_when_export_is_not_written(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr("export_reviews.fetch_reviews", lambda *args, **kwargs: [{"review": "Nice", "author": {}}])
    monkeypatch.setattr("export_reviews.process_reviews", lambda *args, **kwargs: object())
    monkeypatch.setattr("export_reviews.save_to_excel", lambda *args, **kwargs: False)

    assert main(["--app-id", "588650", "--language", "english"]) == 1


def test_run_cli_returns_config_error_for_invalid_config(monkeypatch):
    args = parse_args(["--app-id", "588650", "--language", "english"])

    def raise_validation_error(*args, **kwargs):
        raise pydantic.ValidationError.from_exception_data(
            "ReviewExportConfig",
            [
                {
                    "type": "greater_than",
                    "loc": ("app_id",),
                    "input": 0,
                    "ctx": {"gt": 0},
                }
            ],
        )

    monkeypatch.setattr("export_reviews.get_validated_config", raise_validation_error)

    assert run_cli(args, non_interactive=True) == 2


def test_installed_console_script_entrypoint_points_to_main():
    entry_point = get_console_script_entrypoint()

    assert entry_point.value == "export_reviews:main"
    assert entry_point.load() is main


def test_installed_console_script_wrapper_converts_success_return_code(monkeypatch):
    entry_point = get_console_script_entrypoint()
    cli_main = entry_point.load()
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr(
        "export_reviews.fetch_reviews",
        lambda app_id, language, filter_type, min_len, max_len: [{"review": "Nice", "author": {}}],
    )
    monkeypatch.setattr("export_reviews.process_reviews", lambda reviews, app_id: object())
    monkeypatch.setattr("export_reviews.save_to_excel", lambda *args, **kwargs: True)

    with pytest.raises(SystemExit) as exc_info:
        raise SystemExit(cli_main(["--app-id", "588650", "--language", "english"]))

    assert exc_info.value.code == 0


def test_installed_console_script_wrapper_preserves_parse_error_code():
    entry_point = get_console_script_entrypoint()
    cli_main = entry_point.load()

    with pytest.raises(SystemExit) as exc_info:
        raise SystemExit(cli_main(["--app-id", "588650"]))

    assert exc_info.value.code == 2
