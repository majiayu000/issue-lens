import json,os,re,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
E=Path('/Users/apple/.codex/task-evidence/issue-lens-20261007');O=Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007');ROOT=E/'model-checks';LOG=E/'logs/model-checks';LOG.mkdir(parents=True,exist_ok=True);results=[]
def run(slug,label,args,timeout=300):
 repo=E/'samples'/slug;logs=LOG/slug;logs.mkdir(parents=True,exist_ok=True);log=logs/(str(sum(x['slug']==slug for x in results)+1).zfill(2)+'_'+label+'.log');start=time.monotonic();env=os.environ.copy();env.pop('PYTHONPATH',None);env['NO_COLOR']='1'
 try:
  p=subprocess.run(args,cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);out=p.stdout;code=p.returncode
 except subprocess.TimeoutExpired as ex:
  out=ex.stdout or b'';out=out.decode(errors='replace') if isinstance(out,bytes) else out;out+='\nTASK COMMAND TIMED OUT\n';code=124
 out=re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@',r'\1[redacted]@',out);log.write_text(out);d={'slug':slug,'label':label,'argv':args,'cwd':str(repo),'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(E))};results.append(d);(LOG/'commands_last_five.json').write_text(json.dumps(results,indent=2)+'\n');print(slug,label,code,flush=True);return d
s='tqdm--tqdm';v=E/'venvs/tqdm--tqdm-py314';run(s,'venv_py314',['/opt/homebrew/bin/python3','-m','venv',str(v)]);py=str(v/'bin/python');r=run(s,'install_py314',[py,'-m','pip','--isolated','install','.','pytest','pytest-cov','pytest-timeout','pytest-asyncio']);
if r['exit_code']==0:
 run(s,'environment_py314',[py,'-c','import sys,platform,tqdm;print(sys.version);print(platform.platform());print(tqdm.__file__)']);xml=LOG/s/'native_py314.xml';r=run(s,'native_py314',[py,'-m','pytest','tests/tests_concurrent.py','--junitxml='+str(xml),'-ra']);npath=O/'native_tqdm--tqdm.json';n=json.loads(npath.read_text());n['additional_python314_run']={'commands':[x for x in results if x['slug']==s],'junit':str(xml.relative_to(E)),'status':'passed' if r['exit_code']==0 else 'failed'}
 if xml.exists():
  q=ET.parse(xml).getroot();suites=list(q) if q.tag=='testsuites' else [q];counts={k:sum(int(x.get(k,0)) for x in suites) for k in ['tests','failures','errors','skipped']};counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped'];n['additional_python314_run']['test_counts']=counts
 n['boundary_notes'].append('Original Python3.12 skips retained. Separate available Python3.14 concurrent suite was actually executed; see additional_python314_run.');npath.write_text(json.dumps(n,indent=2)+'\n')
s='cpburnz--python-pathspec';p=str(E/'venvs'/s/'bin/python')
for dep in ['google-re2>=1.1','hyperscan>=0.7']:
 run(s,'optional_'+dep.split('>=')[0],[p,'-m','pip','--isolated','install','--only-binary=:all:',dep])
for s,name in [('tox-dev--filelock','filelock'),('cpburnz--python-pathspec','pathspec'),('tqdm--tqdm','tqdm'),('pypa--packaging','packaging'),('python-humanize--humanize','humanize')]:
 p=str(E/'venvs'/('tqdm--tqdm-py314' if name=='tqdm' else s)/'bin/python');xml=LOG/s/'model_checks.xml';args=[p,'-m','pytest',str(ROOT/('test_'+name+'_cases.py')),'-c',str(E/'samples'/s/'pyproject.toml'),'--junitxml='+str(xml),'-ra','-v'];run(s,'model_checks',args)
 run(s,'freeze',[p,'-m','pip','--isolated','freeze'])
