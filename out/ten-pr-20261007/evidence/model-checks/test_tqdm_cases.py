import operator
from functools import partial
import pytest
from tqdm import tqdm
from tqdm.contrib import concurrent
@pytest.fixture(params=[concurrent.thread_map,concurrent.process_map,concurrent.interpreter_map],ids=['thread','process','interpreter'])
def mapper(request):return request.param
@pytest.fixture
def captured_total(monkeypatch):
    calls=[];original=tqdm.__init__
    def init(self,*args,**kwargs):calls.append(kwargs.get('total'));original(self,*args,**kwargs)
    monkeypatch.setattr(tqdm,'__init__',init)
    return calls

def opts():return {'tqdm_class':tqdm,'max_workers':2,'disable':True}
def test_explicit_total(mapper,captured_total):
    assert mapper(partial(operator.add,1),(i for i in range(9)),total=9,**opts())==list(range(1,10))
    assert captured_total==[9]
def test_empty_unknown(mapper,captured_total):
    assert concurrent._min_map_len([(i for i in ())])==0
    assert mapper(abs,(i for i in ()),**opts())==[]
    assert captured_total==[0]
def test_multiple_unknown_a(mapper,captured_total):
    assert concurrent._min_map_len([(i for i in [1,2,3]),(i for i in [10,20])])==0
    assert mapper(operator.add,(i for i in [1,2,3]),(i for i in [10,20]),**opts())==[11,22]
    assert captured_total==[0]
def test_multiple_unknown_b(mapper,captured_total):
    assert mapper(operator.add,(i for i in range(5)),(i for i in range(10,13)),**opts())==[10,12,14]
    assert captured_total==[0]
def test_mixed_lengths(mapper,captured_total):
    assert concurrent._min_map_len([(i for i in range(9)),range(5)])==5
    assert mapper(operator.add,(i for i in range(9)),range(5),**opts())==[0,2,4,6,8]
    assert captured_total==[5]
def test_worker_error_propagates(mapper):
    with pytest.raises(ValueError,match='worker-failure-marker'):
        mapper(int,(s for s in ['worker-failure-marker']),**opts())
def test_single_unknown_explicit_total_zero(mapper,captured_total):
    assert mapper(partial(operator.add,1),(i for i in range(9)),**opts())==list(range(1,10))
    assert captured_total==[0]
