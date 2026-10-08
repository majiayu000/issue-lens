import json,os,subprocess,time,tomllib
from pathlib import Path
import xml.etree.ElementTree as ET
E=Path('/Users/apple/.codex/task-evidence/issue-lens-20261007');O=Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007');p=O/'native_tox-dev--filelock.json';r=json.loads(p.read_text());repo=Path(r['checkout']);python=E/'venvs/tox-dev--filelock/bin/python';logs=E/'logs/native_tox-dev--filelock'
def run(label,args):
 start=time.monotonic();env=os.environ.copy();env.pop('PYTHONPATH',None);env['NO_COLOR']='1';s=subprocess.run(args,cwd=repo,env=env,capture_output=True,text=True,timeout=600);log=logs/(str(len(r['commands'])+1).zfill(2)+'_'+label+'.log');log.write_text(s.stdout+s.stderr);r['commands'].append({'label':label,'argv':args,'cwd':str(repo),'exit_code':s.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(E))});p.write_text(json.dumps(r,indent=2)+'\n');print(label,s.returncode,flush=True);return s
cfg=tomllib.loads((repo/'pyproject.toml').read_text());deps=[v for v in cfg['dependency-groups']['test'] if not v.startswith('virtualenv')];r['environment_fix']+=' After restoration the actual version is 4.0.6.dev4, still incompatible with virtualenv<4. The selected test_read_write_unit.py and its imported helpers do not use virtualenv; omitted only virtualenv from installation for this focused suite.';r['boundary_notes'].append('Full test dependency group cannot resolve with virtualenv current filelock<4 dependency; focused native suite omits unused virtualenv. This is not full tox/CI validation.')
s=run('install_focused',[str(python),'-m','pip','--isolated','install','.',*deps]);
if s.returncode: r['status']='blocked_dependencies'
else:
 s=run('environment',[str(python),'-c','import platform,sys,filelock;print(sys.version);print(platform.platform());print(filelock.__version__);print(filelock.__file__)']);r['environment']['runtime']=s.stdout.strip();run('freeze',[str(python),'-m','pip','--isolated','freeze']);xml=logs/'junit.xml';s=run('tests',[str(python),'-m','pytest','tests/test_read_write_unit.py','--junitxml='+str(xml),'-ra']);r['status']='passed' if s.returncode==0 else 'failed'
 if xml.exists():
  suites=ET.parse(xml).getroot();suites=list(suites) if suites.tag=='testsuites' else [suites];counts={k:sum(int(x.get(k,0)) for x in suites) for k in ['tests','failures','errors','skipped']};counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped'];r['test_counts']=counts;r['junit']=str(xml.relative_to(E))
r['final_git_status']=subprocess.check_output(['git','status','--short'],cwd=repo,text=True).strip();r['final_head_sha']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();p.write_text(json.dumps(r,indent=2)+'\n')
