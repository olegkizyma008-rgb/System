import pytest


def test_cli_list_editors_prints_known_editors(capsys):
    import tui.cli as cli

    cli.cli_main(["list-editors"])
    out = capsys.readouterr().out
    assert "windsurf" in out


def test_cli_list_modules_unknown_editor_exits_1(capsys):
    import tui.cli as cli

    with pytest.raises(SystemExit) as e:
        cli.cli_main(["list-modules", "--editor", "__unknown__"])
    assert int(e.value.code) == 1
    out = capsys.readouterr().out
    assert "Unknown editor" in out


def test_cli_run_dry_run_exits_0(capsys):
    import tui.cli as cli

    with pytest.raises(SystemExit) as e:
        cli.cli_main(["run", "--editor", "windsurf", "--dry-run"])
    assert int(e.value.code) == 0
    out = capsys.readouterr().out
    assert "[DRY-RUN]" in out
