import concurrent.futures,importlib.util,json,os,pathlib,subprocess
root=pathlib.Path('/Users/apple/.codex/worktrees/issue-lens-comparison-20261007')
spec=importlib.util.spec_from_file_location('experiment',root/'experiments/ten_pr_comparison.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
os.environ['ISSUE_LENS_LLM_ENGINE']='codex';os.environ['ISSUE_LENS_MODEL']='gpt-6.1-sol'
os.environ['GITHUB_TOKEN']=subprocess.check_output(['gh','auth','token','--user','lovedatas'],text=True).strip()
inputs=root/'out/ten-pr-20261007';out=inputs/'runs-1';out.mkdir(exist_ok=False)
manifest=json.loads((inputs/'manifest.json').read_text())
def run(row):
 try:
  result=module.run_sample(json.loads((inputs/row['input']).read_text()),pathlib.Path('/Users/apple/.codex/task-evidence/issue-lens-20261007/issues.db'),out/row['id'])
  print(row['id'],result['status'],flush=True);return {'id':row['id'],'status':result['status']}
 except Exception as e:
  print(row['id'],'failed',type(e).__name__,flush=True);return {'id':row['id'],'status':'failed','error_type':type(e).__name__}
results=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(run,manifest['samples']))
module.save(out/'run.json',{'samples':results,'status':'failed' if any(x['status']=='failed' for x in results) else 'paired_drafts_not_executed'})
