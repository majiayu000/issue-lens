import concurrent.futures,hashlib,json,os,subprocess,pathlib,time
ROOT=pathlib.Path('/Users/apple/.codex/task-evidence/issue-lens-20261007')
OUT=pathlib.Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007/out/ten-pr-20261007')
OUT.mkdir(exist_ok=True)
env={**os.environ,'GH_TOKEN':subprocess.check_output(['gh','auth','token','--user','lovedatas'],text=True).strip()}
selected=[('Textualize/rich',3180),('pallets/click',3865),('fastapi/typer',1821),('theskumar/python-dotenv',700),('tox-dev/platformdirs',566),('tox-dev/filelock',756),('pypa/packaging',1430),('cpburnz/python-pathspec',142),('tqdm/tqdm',1830),('python-humanize/humanize',392)]
def run(args,**kw):
 p=subprocess.run(args,capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(f'{args[0]} failed (exit {p.returncode})')
 return p.stdout

def acquire(item):
 repo,n=item; slug=repo.replace('/','--'); dest=ROOT/'samples'/slug
 meta=json.loads(run(['gh','pr','view',str(n),'-R',repo,'--json','number,title,body,url,headRefOid,baseRefOid,mergedAt,mergeCommit,files'],env=env))
 if not dest.exists():run(['git','clone','--no-checkout','--filter=blob:none','--depth','1','https://github.com/'+repo+'.git',str(dest)])
 run(['git','fetch','--depth','1','origin',f'pull/{n}/head'],cwd=dest)
 run(['git','checkout','--detach','FETCH_HEAD'],cwd=dest)
 sha=run(['git','rev-parse','HEAD'],cwd=dest).strip();assert sha==meta['headRefOid']
 diff=run(['gh','pr','diff',str(n),'-R',repo],env=env)
 files=[f['path'] for f in meta.pop('files')]
 tests=[];code=[];docs=[];instructions=[]
 for p in dest.rglob('AGENTS.md'):
  if '.git' not in p.parts: instructions.append({'path':str(p.relative_to(dest)),'content':p.read_text(errors='replace')})
 for name in files:
  p=dest/name
  if not p.is_file() or p.suffix not in ['.py','.md','.rst']:continue
  s=p.read_text(errors='replace'); entry={'path':name,'content':s,'sha256':hashlib.sha256(s.encode()).hexdigest()}
  if name.startswith('tests/') and p.suffix=='.py':tests.append(entry)
  elif p.suffix=='.py':code.append(entry)
  elif name not in ['CHANGELOG.md','CHANGES.md','CHANGES.rst']:docs.append(entry)
 for name in ['README.md','README.rst','README.rst.txt']:
  if (dest/name).exists():
   s=(dest/name).read_text(errors='replace');docs.append({'path':name,'content':s[:18000],'truncated':len(s)>18000,'sha256':hashlib.sha256(s.encode()).hexdigest()});break
 # Supply bounded but complete affected tests unless over the documented 60k/file bound.
 for i,t in enumerate(tests,1):
  t['id']=f'T{i}';t['truncated']=len(t['content'])>60000;t['content']=t['content'][:60000]
 for c in code:
  c['truncated']=len(c['content'])>60000;c['content']=c['content'][:60000]
 result={'id':slug,'repo':repo,'pr':meta,'head_sha':sha,'checkout':str(dest),'diff':diff,'diff_sha256':hashlib.sha256(diff.encode()).hexdigest(),'tests':tests,'code':code,'docs':docs,'instructions':instructions,'acquired_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (OUT/(slug+'.input.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return {'id':slug,'repo':repo,'number':n,'url':meta['url'],'head_sha':sha,'input':slug+'.input.json','native_test_files':[t['path'] for t in tests]}
rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(acquire,selected))
(OUT/'manifest.json').write_text(json.dumps({'issue_lens_commit':'cb5163970ea7d3ccc41a62207e4bbc390bb1d303','corpus_sha256':hashlib.sha256((ROOT/'issues.db').read_bytes()).hexdigest(),'samples':rows},indent=2))
for row in rows:print(row['id'],row['number'],row['head_sha'][:12],row['native_test_files'])
