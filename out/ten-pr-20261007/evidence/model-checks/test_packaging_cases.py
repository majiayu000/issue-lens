import pytest
from packaging.specifiers import Specifier,SpecifierSet,InvalidSpecifier
from packaging.requirements import Requirement
@pytest.mark.parametrize('s',['===\t',' \t=== \t'])
def test_whitespace_not_version(s):
    with pytest.raises(InvalidSpecifier):Specifier(s)
@pytest.mark.parametrize('s',['>=1,===,<=2','===x,===','=== \t,>=1','>=1, ===\t ,<=2'])
def test_empty_arbitrary_all_set_positions(s):
    with pytest.raises(InvalidSpecifier):SpecifierSet(s)
@pytest.mark.parametrize('s',['===bar===','===arbitrarystring'])
def test_nonempty_three_entries(s):
    spec=Specifier(s);assert spec.operator=='===';assert spec.version==s[3:]
    assert {str(x) for x in SpecifierSet(s)}=={s}
    assert {str(x) for x in Requirement('foo'+s).specifier}=={s}
@pytest.mark.parametrize('s',['===arbitrarystring,>=1','>=1,===arbitrarystring'])
def test_nonempty_mixed_entries(s):
    expected={'===arbitrarystring','>=1'}
    assert {str(x) for x in SpecifierSet(s)}==expected
    assert {str(x) for x in Requirement('foo'+s).specifier}==expected
