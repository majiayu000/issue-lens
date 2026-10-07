import os
import inspect
from pathlib import Path

import pytest
import platformdirs
from platformdirs.unix import Unix
from platformdirs.windows import Windows


def test_B_TC001_private_storage_and_public_attributes():
    dirs = platformdirs.PlatformDirs("app", "author", "1.0")
    for name, value in [ ("appname", "app"), ("appauthor", "author"), ("version", "1.0") ]:
        assert vars(dirs)["_" + name] == value
        assert name not in vars(dirs)
        assert getattr(dirs, name) == value
        setattr(dirs, name, "new")
        assert getattr(dirs, name) == vars(dirs)["_" + name] == "new"
        with pytest.raises(ValueError):
            setattr(dirs, name, "../escaped")
        assert getattr(dirs, name) == vars(dirs)["_" + name] == "new"
        setattr(dirs, name, None)
        assert getattr(dirs, name) == vars(dirs)["_" + name] is None


@pytest.mark.parametrize("field", ["appname", "appauthor", "version"])
@pytest.mark.parametrize("invalid", ["../escaped", "../evil", "nested/../../evil", "..\\evil", "/evil", "\\evil", "//server/share/evil"])
def test_A_TC003_B_TC002_unix_component_no_escape_after_rejected_assignment(tmp_path, monkeypatch, field, invalid):
    base = tmp_path / "base"
    sentinel = tmp_path / "owned-sentinel"
    sentinel.write_text("unchanged")
    monkeypatch.setenv("XDG_DATA_HOME", str(base))
    dirs = Unix("app", "author", "1.0", ensure_exists=True, use_site_for_root=False)
    original = getattr(dirs, field)
    with pytest.raises(ValueError):
        setattr(dirs, field, invalid)
    assert getattr(dirs, field) == original
    result = Path(dirs.user_data_dir)
    assert result == dirs.user_data_path
    assert result.is_relative_to(base)
    assert result.is_dir()
    assert not (tmp_path / "escaped").exists()
    assert set(tmp_path.iterdir()) == {base, sentinel}
    assert sentinel.read_text() == "unchanged"


def test_B_TC003_none_public_api_and_mock_windows(monkeypatch):
    for name in ["appname", "appauthor", "version"]:
        values = {"appname": "app", "appauthor": "author", "version": "1.0"}
        values[name] = None
        dirs = platformdirs.PlatformDirs(**values)
        assert getattr(dirs, name) is None
        assert isinstance(dirs.user_data_dir, str)
        dirs = platformdirs.PlatformDirs("app", "author", "1.0")
        setattr(dirs, name, None)
        assert getattr(dirs, name) is None
        assert isinstance(dirs.user_data_dir, str)
    monkeypatch.setattr("platformdirs.windows.get_win_folder", lambda _: "C:/Local")
    for author, expected in [(False, "C:/Local/app/1.0"), (None, "C:/Local/app/app/1.0")]:
        constructed = Windows("app", author, "1.0")
        assert Path(constructed.user_data_dir) == Path(os.path.normpath(expected))
        assigned = Windows("app", "author", "1.0")
        assigned.appauthor = author
        assert Path(assigned.user_data_dir) == Path(os.path.normpath(expected))
    assert "name of the application" in platformdirs.PlatformDirs.appname.__doc__
    assert "False" in platformdirs.PlatformDirs.appauthor.__doc__
    assert "None" in platformdirs.PlatformDirs.appauthor.__doc__
    assert "version path element" in platformdirs.PlatformDirs.version.__doc__


def test_A_TC001_public_construction_assignment_docs():
    for dirs in [platformdirs.PlatformDirs("app", "author", "1.0"),
                 platformdirs.PlatformDirs(appname="app", appauthor="author", version="1.0")]:
        assert (dirs.appname, dirs.appauthor, dirs.version) == ("app", "author", "1.0")
        for name in ["appname", "appauthor", "version"]:
            setattr(dirs, name, "new")
            assert getattr(dirs, name) == "new"
    parameters = inspect.signature(platformdirs.PlatformDirs.__init__).parameters
    assert all(name in parameters for name in ["appname", "appauthor", "version"])
    assert "name of the application" in platformdirs.PlatformDirs.appname.__doc__
    assert "False" in platformdirs.PlatformDirs.appauthor.__doc__
    assert "None" in platformdirs.PlatformDirs.appauthor.__doc__
    assert "version path element" in platformdirs.PlatformDirs.version.__doc__
