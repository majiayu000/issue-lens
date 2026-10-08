"""Deliberately retry only missing arms from a failed frozen run; never overwrite it.

python3 out/ten-pr-20261007/evidence/retry_exact.py SOURCE_RUN NEW_OUTPUT
Uses the same model, prompt and exact supplied inputs. Keeps successful original arms.
"""
import hashlib,json,os,pathlib,sys,time
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root))
from llm import generate_json,ModelError
from s05_plan import PLAN_PROMPT,validate_plan
src=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=False)
old=json.loads((src/'status.json').read_text());assert os.environ.get('ISSUE_LENS_MODEL')==old['requested_model']
status={**old,'retry_of':str(src),'stages':{},'status':'running','retry_policy':'one deliberate retry per missing arm, identical frozen input'}
def save(name,data):(dest/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
try:
 for arm in old['order']:
  if (src/(arm+'.json')).exists():
   for suffix in ['.json','.input.json']:(dest/(arm+suffix)).write_bytes((src/(arm+suffix)).read_bytes())
   status['stages'][arm]={'status':'reused_valid_original','seconds':0};continue
  # First failed arm may have stopped the runner before writing the other arm.
  if (src/(arm+'.input.json')).exists():inputs=json.loads((src/(arm+'.input.json')).read_text())
  else:
   inputs=json.loads((src/'B.input.json').read_text());inputs['sources']=[] if arm=='A' else inputs['sources']
  save(arm+'.input.json',inputs);start=time.monotonic()
  plan,provenance=generate_json(PLAN_PROMPT,inputs)
  validate_plan(plan,inputs['requirements'],inputs['sources'],inputs['tests'])
  status['stages'][arm]={'status':'completed','seconds':time.monotonic()-start}
  def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  common={k:v for k,v in inputs.items() if k!='sources'}
  assert digest(common)==old['common_input_sha256']
  assert hashlib.sha256(PLAN_PROMPT.encode()).hexdigest()==old['prompt_sha256']
  save(arm+'.json',{'status':'draft_not_executed','plan':plan,'generation':provenance,
                   'input_sha256':digest(inputs),'common_input_sha256':digest(common),'prompt_sha256':old['prompt_sha256']})
 status['status']='paired_drafts_not_executed';save('status.json',status)
except Exception as e:
 status['status']='failed_no_pair_accepted';status['stages'][arm]={'status':'failed','seconds':time.monotonic()-start,'error_type':type(e).__name__}
 if isinstance(e,ModelError):status['stages'][arm]['error']=str(e)
 save('status.json',status);raise SystemExit(1)
print(old['sample'],status['status'])
