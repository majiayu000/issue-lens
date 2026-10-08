import pytest
from click.testing import CliRunner
from dotenv.cli import cli


@pytest.mark.parametrize("contents", ['a=""\n', "a=''\n"])
def test_A_TC001_B_TC001_quoted_empty(tmp_path, contents):
    path = tmp_path / "quoted.env"
    path.write_text(contents)
    result = CliRunner().invoke(cli, ["--file", str(path), "get", "a"])
    assert (result.exit_code, result.output) == (0, "\n")


def test_A_TC002_B_TC002_missing_key_nonempty_file(tmp_path):
    path = tmp_path / "nonempty.env"
    path.write_text("b=value\n")
    result = CliRunner().invoke(cli, ["--file", str(path), "get", "a"])
    assert (result.exit_code, result.output) == (1, "")

