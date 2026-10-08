import typer
from typer.testing import CliRunner


def test_A_TC001_required_list_missing_stays_usage_error():
    app = typer.Typer()
    executed = []

    @app.command()
    def required(names: list[str]):
        executed.append(names)

    result = CliRunner().invoke(app, [])
    assert result.exit_code != 0
    assert "Missing argument" in result.output
    assert "Traceback" not in result.output
    assert executed == []


def test_A_TC002_envvar_absent_and_present(monkeypatch):
    app = typer.Typer()

    @app.command()
    def hello(names: list[str] = typer.Argument(["World"], envvar="NAMES")):
        for name in names:
            print(f"Hello {name}!")

    monkeypatch.delenv("NAMES", raising=False)
    result = CliRunner().invoke(app, [])
    assert (result.exit_code, result.output) == (0, "Hello World!\n")
    monkeypatch.setenv("NAMES", "Rick   Morty")
    result = CliRunner().invoke(app, [])
    assert (result.exit_code, result.output) == (0, "Hello Rick!\nHello Morty!\n")


def test_B_TC001_explicit_empty_string_is_one_element():
    app = typer.Typer()
    received = []

    @app.command()
    def hello(names: list[str] = typer.Argument(["World"])):
        received.append(names)

    result = CliRunner().invoke(app, [""])
    assert result.exit_code == 0
    assert received == [[""]]


def test_B_TC002_envvar_actual_lists(monkeypatch):
    app = typer.Typer()
    received = []

    @app.command()
    def hello(names: list[str] = typer.Argument(["World"], envvar="NAMES")):
        received.append(names)

    monkeypatch.delenv("NAMES", raising=False)
    assert CliRunner().invoke(app, []).exit_code == 0
    monkeypatch.setenv("NAMES", "Rick   Morty")
    assert CliRunner().invoke(app, []).exit_code == 0
    assert received == [["World"], ["Rick", "Morty"]]

