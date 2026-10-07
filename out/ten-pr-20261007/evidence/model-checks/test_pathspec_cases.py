import re
import pytest
from pathspec import PathSpec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern
from pathspec.patterns.gitignore.spec import GitIgnoreSpecPattern
BS='\\'
@pytest.mark.parametrize('cls',[GitIgnoreBasicPattern,GitIgnoreSpecPattern])
@pytest.mark.parametrize('n',[1,2,3])
def test_bytes_odd_even(cls,n):
    raw=('foo'+BS*n+' ').encode('ascii');regex,include=cls.pattern_to_regex(raw)
    assert isinstance(regex,bytes);assert include is True
    expected=('foo'+BS*(n//2)+(' ' if n%2 else '')).encode('ascii');other=expected.rstrip() if n%2 else expected+b' '
    assert re.compile(regex).search(expected) is not None
    assert re.compile(regex).search(other) is None
    if n==2:assert regex==cls.pattern_to_regex(raw[:-1])[0]
@pytest.mark.parametrize('cls',[GitIgnoreBasicPattern,GitIgnoreSpecPattern])
def test_leading_space_with_even_trailing(cls):
    p=cls(' foo'+BS*2+' ')
    assert p.match_file(' foo'+BS) is not None
    assert p.match_file('foo'+BS) is None
    assert p.match_file(' foo'+BS+' ') is None
@pytest.mark.parametrize('backend',['simple','re2','hyperscan'])
def test_explicit_backend_odd_even(backend):
    try:p=PathSpec.from_lines('gitignore',['foo'+BS*2+' '],backend=backend)
    except (ImportError,ModuleNotFoundError) as exc:pytest.skip(str(exc))
    assert p.match_file('foo'+BS,separators=('/',)) is True
    assert p.match_file('foo'+BS+' ',separators=('/',)) is False
    p=PathSpec.from_lines('gitignore',['foo'+BS+' '],backend=backend)
    assert p.match_file('foo ',separators=('/',)) is True
    assert p.match_file('foo',separators=('/',)) is False
