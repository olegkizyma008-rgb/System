import pytest


def test_cli_list_editors_prints_known_editors(capsys):
    import tui.cli as cli

    cli.cli_main(["list-editors"])
    out = capsys.readouterr().out
    assert "windsurf" in out


def test_cli_list_modules_unknown_editor_exits_1(capsys):
    import tui.cli as cli

    cli.cli_main(["list-modules", "--editor", "__unknown__"])
    captured = capsys.readouterr()
    assert "Editor not specified" in captured.err
    assert "[" in captured.out


def test_cli_run_dry_run_exits_0(capsys):
    import tui.cli as cli

    with pytest.raises(SystemExit) as e:
        cli.cli_main(["run", "--editor", "windsurf", "--dry-run"])
    assert int(e.value.code) == 0
    out = capsys.readouterr().out
    assert "[DRY-RUN]" in out


def test_cli_list_modules_without_editor_falls_back(capsys):
    import tui.cli as cli

    cli.cli_main(["list-modules"])
    captured = capsys.readouterr()
    assert "Editor not specified" in captured.err
    assert "[" in captured.out


def test_cli_run_without_editor_dry_run_falls_back(capsys):
    import tui.cli as cli

    with pytest.raises(SystemExit) as e:
        cli.cli_main(["run", "--dry-run"])
    assert int(e.value.code) == 0
    captured = capsys.readouterr()
    assert "Editor not specified" in captured.err
    assert "[DRY-RUN]" in captured.out
