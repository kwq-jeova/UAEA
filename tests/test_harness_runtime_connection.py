
import json,sys,tempfile,tomllib,unittest
from pathlib import Path
from unittest.mock import patch
U=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(U/'scripts'))
import h3_harness_interactive_repl as h
from h3_context_characterization import write_config
from harness.io_contract import turn_context_payload
class ConnectionSettingsTests(unittest.TestCase):
 def test_existing_profile_default_effort_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   write_config(Path(d),'http://127.0.0.1:8000',32768,model='Qwen2.5-14B-Instruct-AWQ',n1x=True)
   c=tomllib.loads((Path(d)/'config.toml').read_text())
   self.assertEqual(c['model_reasoning_effort'],'none')
   self.assertEqual(c['model'],'Qwen2.5-14B-Instruct-AWQ')
 def test_bolt_effort_and_endpoint_are_configurable(self):
  with tempfile.TemporaryDirectory() as d:
   write_config(Path(d),'http://127.0.0.1:8003',32768,model='nemotron-bolt-n1x',n1x=True,reasoning_effort='low')
   c=tomllib.loads((Path(d)/'config.toml').read_text())
   self.assertEqual(c['model_reasoning_effort'],'low')
   self.assertEqual(c['model_providers']['uaea_local_vllm']['base_url'],'http://127.0.0.1:8003/v1')
 def test_file_root_is_separate_fact_without_rewriting_other_contracts(self):
  with patch('harness.io_contract.datetime') as clock:
   clock.now.return_value.isoformat.return_value='2026-11-05T00:00:00+00:00'
   original=turn_context_payload([])
   augmented=turn_context_payload([],filesystem_root='/test/project')
  fact=augmented.pop('uaea.runtime_facts.filesystem')
  self.assertEqual(augmented,original)
  self.assertEqual(fact['kind'],'application')
  self.assertIn('/test/project/README.md',fact['value'])
  with self.assertRaises(ValueError):turn_context_payload([],filesystem_root='relative')
 def test_connection_cli_keeps_platform_checks(self):
  with patch('harness.version_manifest.current_platform',return_value='linux-aarch64'),patch('harness.version_manifest.selected_harness',return_value={'binary':'/tmp/codex','tag':'rust-v0.163.0'}),patch('harness.version_manifest.identify_harness',return_value={'build_target':'aarch64-unknown-linux-gnu'}):
   a=h.parse_args(['--profile','n1x','--model','nemotron-bolt-n1x','--base-url','http://127.0.0.1:8003','--reasoning-effort','low'])
   self.assertEqual(a.reasoning_effort,'low')
   self.assertEqual(a.context,32768)
if __name__=='__main__':unittest.main()
