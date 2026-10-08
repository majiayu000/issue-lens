import threading,time
from contextlib import closing
import pytest
from filelock import ReadWriteLock,SoftReadWriteLock,Timeout

@pytest.fixture(params=[ReadWriteLock,SoftReadWriteLock],ids=['sqlite','soft'])
def locks(tmp_path,request):
    with closing(request.param(tmp_path/'a',timeout=-2,is_singleton=False)) as holder,closing(request.param(tmp_path/'a',is_singleton=False)) as contender:
        yield holder,contender

def state(lock):
    if isinstance(lock,ReadWriteLock):return lock._lock_level,lock._current_mode
    return (lock._hold.level,lock._hold.mode) if lock._hold else (0,None)

@pytest.mark.parametrize('mode',['read','write'])
def test_defaults_and_overrides(locks,mode):
    h,c=locks;a=getattr(h,'acquire_'+mode)
    with a(timeout=-1):
        for kwargs in [{},{'timeout':None,'blocking':None}]:
            with pytest.raises(ValueError,match='^timeout must be a non-negative number or -1$'):a(**kwargs)
            assert state(h)==(1,mode)
        with a(timeout=-1,blocking=True):assert state(h)==(2,mode)
        with a(blocking=False):assert state(h)==(2,mode)
        assert state(h)==(1,mode)
    with c.acquire_write(blocking=False):pass

@pytest.mark.parametrize('mode',['read','write'])
def test_multilayer_failure_preserves_hold(locks,mode):
    h,c=locks;a=getattr(h,'acquire_'+mode)
    with a(timeout=-1):
        with a(timeout=-1):
            with pytest.raises(ValueError):a(timeout=-2,blocking=True)
            assert state(h)==(2,mode)
            with pytest.raises(Timeout):c.acquire_write(blocking=False)
        assert state(h)==(1,mode)
        with pytest.raises(Timeout):c.acquire_write(blocking=False)
    with c.acquire_write(blocking=False):pass

@pytest.mark.parametrize('mode',['read','write'])
def test_unlimited_wait_then_reentrant(locks,mode):
    h,c=locks;started=threading.Event();done=threading.Event();errors=[]
    def worker():
        try:
            started.set()
            with getattr(c,'acquire_'+mode)(timeout=-1,blocking=True):
                with getattr(c,'acquire_'+mode)(timeout=-1,blocking=True):assert state(c)==(2,mode)
        except BaseException as exc:errors.append(exc)
        finally:done.set()
    with h.acquire_write(timeout=-1):
        t=threading.Thread(target=worker,daemon=True);t.start();assert started.wait(5);assert not done.wait(.15)
    t.join(10);assert not t.is_alive();assert not errors;assert done.is_set()
    with h.acquire_write(timeout=-1,blocking=False):pass

@pytest.mark.parametrize('mode',['read','write'])
@pytest.mark.parametrize('timeout',[-2,-.5,float('-inf'),5.0])
def test_nonblocking_timeout_under_contention(locks,mode,timeout):
    h,c=locks;a=getattr(c,'acquire_'+mode)
    with a(timeout=timeout,blocking=False):
        with a(timeout=timeout,blocking=False):pass
    with h.acquire_write(timeout=-1):
        start=time.monotonic()
        with pytest.raises(Timeout):a(timeout=timeout,blocking=False)
        assert time.monotonic()-start<1
    with a(timeout=timeout,blocking=False):pass
