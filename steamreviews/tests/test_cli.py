import pytest

from export_reviews import get_validated_config, main, parse_args


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


def test_main_does_not_prompt_again_in_non_interactive_mode(monkeypatch):
    monkeypatch.setattr("export_reviews.get_game_name", lambda app_id: "Dead Cells")
    monkeypatch.setattr(
        "export_reviews.fetch_reviews",
        lambda app_id, language, filter_type, min_len, max_len: [{"review": "Nice", "author": {}}],
    )
    monkeypatch.setattr("export_reviews.process_reviews", lambda reviews, app_id: object())
    monkeypatch.setattr("export_reviews.save_to_excel", lambda *args, **kwargs: None)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail(f"Unexpected prompt: {prompt}"))

    main(["--app-id", "588650", "--language", "english"])
