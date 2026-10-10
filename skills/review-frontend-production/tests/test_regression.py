"""Synthetic declarations test ledger mechanics, not product behavior."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
L=load('audit_ledger');D=load('discover_frontend')
class Regression(unittest.TestCase):
    def setUp(self):
        self.d=json.loads((ROOT/'examples/source-only/audit.json').read_text(encoding='utf-8'))
    def invalid(self): self.assertFalse(L.validate(self.d)['schema_valid'])
    def test_sample(self):
        r=L.validate(self.d)
        self.assertTrue(r['schema_valid']);self.assertTrue(r['plan_complete'])
        self.assertFalse(r['audit_coverage_closed']);self.assertFalse(r['production_gates_satisfied'])
    def test_sync_preserves_decisions(self):
        before=json.dumps(self.d['checks']);self.assertEqual(L.sync_checks(self.d),0)
        self.assertEqual(before,json.dumps(self.d['checks']))
    def test_failed_needs_confirmed_finding(self):
        self.d['findings'][0]['confidence']='needs_validation';self.invalid()
    def test_scenario_needs_execution(self):
        self.d['scenarios'][0].update(status='passed',evidence_ids=['EV-001']);self.invalid()
    def test_parent_cycle(self):
        self.d['instances'][0]['parent_instance_id']='CMP-002'
        self.d['instances'][1]['parent_instance_id']='CMP-001';self.invalid()
    def test_wrong_regression_instance(self):
        self.d['scenarios'][0]['instance_ids'].remove('CMP-003');self.invalid()
    def test_missing_blueprint(self):
        self.d['definitions'].append(dict(self.d['definitions'][0],id='DEF-004'))
        r=L.validate(self.d);self.assertTrue(r['schema_valid']);self.assertFalse(r['plan_complete'])
    def test_task_cycle(self):
        self.d['tasks'][0]['depends_on']=['TASK-001'];self.invalid()
    def test_resolved_cannot_keep_failed_check(self):
        self.d['findings'][0].update(status='resolved',resolution_evidence_ids=['EV-001']);self.invalid()
    def test_verified_needs_execution(self):
        self.d['tasks'][0].update(status='verified',evidence_ids=['EV-001']);self.invalid()
    def test_quick_gate(self):
        self.d['findings'][0].update(status='dismissed',decision={'reason':'synthetic','authority':'test'})
        for c in self.d['checks']: c.update(status='not_applicable',reason='synthetic test scope',finding_ids=[])
        self.d['scenarios'][0].update(status='passed',evidence_ids=['EV-002'])
        self.assertTrue(L.validate(self.d)['audit_coverage_closed'])
        self.d['project']['review_depth']='quick';r=L.validate(self.d)
        self.assertTrue(r['schema_valid'])
        for k in ['audit_coverage_closed','plan_complete','production_gates_satisfied']: self.assertFalse(r[k])
    def test_legacy_depth(self):
        self.d['project'].pop('review_depth');self.assertTrue(L.validate(self.d)['plan_complete'])
    def test_invalid_depth(self):
        self.d['project']['review_depth']='typo';self.invalid()
    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'audit.json'
            def run(*args):
                return subprocess.run([sys.executable,'-B',str(ROOT/'scripts/audit_ledger.py'),*map(str,args)],capture_output=True).returncode
            self.assertEqual(run('init',p,'--name','test'),0)
            self.assertEqual(run('init',p,'--name','test'),1)
            self.assertEqual(run('check',p),0)
            self.assertEqual(run('check',p,'--require-complete'),2)
            self.assertEqual(run('render',p,'--out',p),1)
            p.write_text('{bad');self.assertEqual(run('check',p),1)
    def test_discovery_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'App.tsx').write_text('export function App(){return <a href="/about">About</a>}')
            (p/'package.json').write_text(json.dumps({'scripts':{'build':'exit 77'},'dependencies':{'react':'test'}}))
            r=D.discover(p)
            self.assertEqual(r['path_literal_candidates'][0]['value'],'/about')
            self.assertEqual(r['component_declaration_candidates'][0]['name'],'App')
            self.assertEqual(r['packages'][0]['script_names'],['build'])
    def test_external_symlink_and_env_excluded(self):
        with tempfile.TemporaryDirectory() as tmp,tempfile.TemporaryDirectory() as outside:
            p=Path(tmp);s=Path(outside)/'external.tsx';s.write_text('const ExternalSecret = 1')
            (p/'link.tsx').symlink_to(s);(p/'.env').write_text('SECRET=fixture')
            r=json.dumps(D.discover(p));self.assertNotIn('ExternalSecret',r);self.assertNotIn('SECRET',r)
    def test_large_file_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'App.tsx').write_text('x'*100)
            r=D.discover(p,max_bytes=10);self.assertTrue(r['skipped']);self.assertFalse(r['component_declaration_candidates'])
if __name__=='__main__': unittest.main()
