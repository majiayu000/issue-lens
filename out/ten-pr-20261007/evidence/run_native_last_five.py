import json, os, platform, re, subprocess, time, tomllib
from pathlib import Path
import xml.etree.ElementTree as ET
E = Path('/Users/apple/.codex/task-evidence/issue-lens-20261007')
O = Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007')
SLUGS = ['tox-dev--filelock','pypa--packaging','cpburnz--python-pathspec','tqdm--tqdm','python-humanize--humanize']
NOTES = {
 'tox-dev--filelock': ['Timeout validation covers SQLite and soft read/write locks, first/reentrant read/write acquisitions; original ValueError, Timeout and hold preservation must remain intact.','Hard links are available on this macOS run; Windows, Linux, other Python versions and network filesystem behavior are not established.'],
 'pypa--packaging': ['Empty arbitrary versions are rejected by Specifier, SpecifierSet and Requirement; nonempty arbitrary strings and mixed lists must remain accepted.','Project defaults exclude property tests; this is the diff-related deterministic native suite.'],
 'cpburnz--python-pathspec': ['Native runner is unittest. Both basic/spec pattern compilers and PathSpec are covered; odd/even backslash runs must retain Git-compatible trailing-space semantics.','Optional hyperscan/re2 backends and Windows separator behavior are not established by this base-backend macOS run.'],
 'tqdm--tqdm': ['No-known-length iterable fallback and known/unknown mixture semantics are exercised through native concurrent map tests.','Python 3.12 lacks InterpreterPoolExecutor; interpreter_map branches require Python 3.14+ and are expected skips.'],
 'python-humanize--humanize': ['Large positive/negative integers must avoid float conversion while finite/nonfinite values and existing formatting behavior retain the original contract.','Only Python 3.12/macOS is covered; this result is not a full locale/platform/version matrix.']}
for slug in SLUGS:
 d=json.loads((O/(slug+'.input.json')).read_text()); repo=Path(d['checkout']); logs=E/'logs'/('native_'+slug);logs.mkdir(parents=True,exist_ok=True)
 venv=E/'venvs'/slug;python=venv/'bin/python'
 def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
 assert git('rev-parse','HEAD') == d['head_sha']
 report={'id':slug,'repo':d['repo'],'pr':d['pr']['number'],'head_sha':d['head_sha'],'checkout':str(repo),'environment':{'platform':platform.platform(),'base_python':'/Users/apple/.local/bin/python3.12','venv':str(venv)},'commands':[],'initial_git_status':git('status','--short'),'native_test_files':[x['path'] for x in d['tests']],'boundary_notes':NOTES[slug],'maintainer_adoption':'not evaluated by a human maintainer','historical_gain':'not established by native baseline'}
 def run(label,args,timeout=600):
  log=logs/(str(len(report['commands'])+1).zfill(2)+'_'+label+'.log');start=time.monotonic()
  env=os.environ.copy();env.pop('PYTHONPATH',None);env['PIP_DISABLE_PIP_VERSION_CHECK']='1';env['NO_COLOR']='1'
  try:
   p=subprocess.run(args,cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout); code=p.returncode;out=p.stdout
  except subprocess.TimeoutExpired as ex:code=124;out=(ex.stdout or b'');out=out.decode(errors='replace') if isinstance(out,bytes) else out;out+='\nTASK COMMAND TIMED OUT\n'
  out=re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@',r'\1[redacted]@',out)
  log.write_text(out);entry={'label':label,'argv':args,'cwd':str(repo),'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(E))};report['commands'].append(entry);print(slug,label,code,entry['elapsed_seconds'],flush=True)
  (O/('native_'+slug+'.json')).write_text(json.dumps(report,indent=2)+'\n');return code,out
 code,_=run('venv',['/Users/apple/.local/bin/python3.12','-m','venv',str(venv)])
 if code:report['status']='blocked_environment';(O/('native_'+slug+'.json')).write_text(json.dumps(report,indent=2)+'\n');continue
 cfg=tomllib.loads((repo/'pyproject.toml').read_text())
 if slug=='python-humanize--humanize':deps=cfg['project']['optional-dependencies']['tests']
 elif slug=='tqdm--tqdm':deps=['pytest','pytest-cov','pytest-timeout','pytest-asyncio']
 else:deps=cfg['dependency-groups']['dev' if slug=='cpburnz--python-pathspec' else 'test']
 code,_=run('install',[str(python),'-m','pip','--isolated','install','.',*deps])
 if code:report['status']='blocked_dependencies';(O/('native_'+slug+'.json')).write_text(json.dumps(report,indent=2)+'\n');continue
 _,out=run('environment',[str(python),'-c','import platform,sys;print(sys.version);print(platform.platform())'])
 report['environment']['runtime']=out.strip();run('freeze',[str(python),'-m','pip','--isolated','freeze'])
 if slug=='cpburnz--python-pathspec':
  args=[str(python),'-m','unittest','discover','-t','.','-s','tests/','-p','test_07_gitignore_trailing_space.py','-v'];code,out=run('tests',args);m=re.search(r'Ran (\d+) tests?',out);report['test_counts']={'run':int(m[1]) if m else None,'passed':int(m[1]) if m and code==0 else None};report['test_count_unit']='unittest test methods; subTests not counted as separate tests'
 else:
  xml=logs/'junit.xml';args=[str(python),'-m','pytest',*report['native_test_files'],'--junitxml='+str(xml),'-ra'];code,out=run('tests',args)
  if xml.exists():
   suites=ET.parse(xml).getroot();suites=list(suites) if suites.tag=='testsuites' else [suites];counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped'];report['test_counts']=counts;report['junit']=str(xml.relative_to(E))
 report['status']='passed' if code==0 else 'failed';report['final_git_status']=git('status','--short');report['final_head_sha']=git('rev-parse','HEAD');(O/('native_'+slug+'.json')).write_text(json.dumps(report,indent=2)+'\n')
