import sys
from tqdm.auto import tqdm
from tqdm.contrib.concurrent import interpreter_map,process_map

def main():
    before=tqdm.get_lock()
    print('before_lock_type',type(before).__name__)
    mode=sys.argv[1] if len(sys.argv)>1 else 'error'
    values=['1','2'] if mode=='success' else ['worker-failure-marker']
    inputs=values if mode=='known-error' else (s for s in values)
    try:
        interpreter_map(int,inputs,max_workers=2,disable=True)
    except ValueError as exc:
        print('expected_worker_error',type(exc).__name__,str(exc))
    else:
        if mode!='success':raise AssertionError('worker error did not propagate')
    after=tqdm.get_lock()
    print('after_lock_type',type(after).__name__,'same_object',after is before)
    print('next_process_map')
    result=process_map(abs,(n for n in [-1,-2]),max_workers=2,disable=True)
    print('result',result)
    assert result==[1,2]
    assert after is before,'worker failure leaked global progress lock'

if __name__=='__main__':main()
