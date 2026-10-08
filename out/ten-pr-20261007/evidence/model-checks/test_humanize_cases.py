import pytest
import humanize

def grouped(v):
    s=str(v);sign=''
    if s.startswith('-'):sign='-';s=s[1:]
    groups=[]
    while s:groups.append(s[-3:]);s=s[:-3]
    return sign+','.join(reversed(groups))
def test_explicit_none_large_integer():
    v=10**400+123;expected='10'+',000'*132+',123'
    assert humanize.intcomma(v)==humanize.intcomma(v,ndigits=None)==expected

def test_dense_adjacent_large_integers():
    a=123456789*10**312+9007199254740992;b=a+1
    aa=humanize.intcomma(a);bb=humanize.intcomma(b)
    assert aa==grouped(a);assert bb==grouped(b);assert aa!=bb
    assert aa.endswith(',992');assert bb.endswith(',993')

def test_dense_405_digits():
    digits='123456789'*45;v=int(digits);result=humanize.intcomma(v)
    assert result==grouped(v)
    assert result.replace(',','')==digits
