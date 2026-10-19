"""Regression tests for the concrete v0.1 audit findings."""
import copy
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from blackbox.storage import Ledger, RunBusy, LostLease, WorkflowLock, digest
from blackbox.contracts import validate_request
from blackbox.registry import ROOT, publish, verify, select, identity, load_artifact
from blackbox.cache import collection_identity, load, save, COLLECTION_FILES
from blackbox.provenance import execution_identity, source_hash
from test_policy import feasible_state, request


class MLOpsTests(unittest.TestCase):
    def test_workflow_lock_is_exclusive_and_releases_on_close(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'workflow.lock'
            with WorkflowLock(path):
                with self.assertRaises(RunBusy):
                    with WorkflowLock(path):pass
            with WorkflowLock(path):pass

    def test_duplicate_worker_cannot_claim_live_run(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runs.sqlite';a=Ledger(path);b=Ledger(path)
            a.claim({'seed':1})
            with self.assertRaises(RunBusy):b.claim({'seed':1})
            a.close();b.close()

    def test_failure_retained_after_retry(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=Ledger(Path(d)/'runs.sqlite')
            key,_=ledger.claim({'seed':1});ledger.finish(key,{'valid':False,'error':'illegal action'})
            key,_=ledger.claim({'seed':1});ledger.finish(key,{'valid':True})
            audit=ledger.audit()
            self.assertEqual([a['status'] for a in audit],['failed','completed'])
            self.assertEqual(audit[0]['error'],'illegal action');ledger.close()

    def test_expired_owner_cannot_commit_reclaimed_run(self):
        clock=[100.0]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runs.sqlite'
            a=Ledger(path,lease_seconds=10,clock=lambda:clock[0]);b=Ledger(path,lease_seconds=10,clock=lambda:clock[0])
            key,_=a.claim({'seed':1});clock[0]=111
            b.claim({'seed':1})
            with self.assertRaises(LostLease):a.finish(key,{'valid':True})
            b.finish(key,{'valid':True});self.assertEqual(b.audit()[0]['status'],'interrupted')
            a.close();b.close()

    def test_heartbeat_prevents_early_reclaim(self):
        clock=[100.0]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runs.sqlite'
            a=Ledger(path,lease_seconds=10,clock=lambda:clock[0]);b=Ledger(path,lease_seconds=10,clock=lambda:clock[0])
            key,_=a.claim({'seed':1});clock[0]=109;a.heartbeat(key);clock[0]=111
            with self.assertRaises(RunBusy):b.claim({'seed':1})
            a.close();b.close()

    def test_backup_restores_audit_and_completed_result(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runs.sqlite';ledger=Ledger(path)
            key,_=ledger.claim({'seed':1});ledger.finish(key,{'valid':True,'score':3})
            dest=sqlite3.connect(Path(d)/'backup.sqlite');ledger.db.backup(dest);dest.close();ledger.close()
            restored=Ledger(Path(d)/'backup.sqlite')
            self.assertEqual(restored.db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(restored.claim({'seed':1})[1]['score'],3);self.assertEqual(len(restored.audit()),1);restored.close()

    def test_hard_field_type_and_category_rejection(self):
        cases={'has_children':'false','age_min':True,'age_max':17,'who_to_meet':['alien'],
               'relationship_structure':'unknown','smoking':'sometimes','partner_smoking':False,
               'partner_children':0,'wants_children':'maybe','acceptable_zones':[],
               'schedule':['wrong_slot']}
        for field,value in cases.items():
            with self.subTest(field=field):
                state=feasible_state();state['members'][0]['fields'][field]=value
                with self.assertRaises(ValueError):validate_request(request(state))

    def test_inverted_age_bounds_and_negative_observation_rejected(self):
        state=feasible_state();state['members'][0]['fields'].update(age_min=40,age_max=30)
        with self.assertRaises(ValueError):validate_request(request(state))
        state=feasible_state();state['members'][0]['field_observed_day']['schedule']=-1
        with self.assertRaises(ValueError):validate_request(request(state))

    def test_nonfinite_memory_and_boolean_arrival_rejected(self):
        r=request(feasible_state());r['memory']=float('inf')
        with self.assertRaises(ValueError):validate_request(r)
        state=feasible_state();state['members'][0]['arrived_day']=False
        with self.assertRaises(ValueError):validate_request(request(state))

    def test_cache_identity_tracks_feature_and_generator_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in COLLECTION_FILES:
                (root/name).parent.mkdir(parents=True,exist_ok=True);(root/name).write_text('original')
            first=collection_identity(1101,'development','baseline_greedy',root)
            (root/'blackbox/features.py').write_text('changed')
            second=collection_identity(1101,'development','baseline_greedy',root)
            self.assertNotEqual(first,second)
            p=root/'cache.json';save(p,first,{'rows':[]})
            with self.assertRaises(ValueError):load(p,second)

    def test_corrupt_cache_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cache.json';save(p,{'v':1},{'rows':[1]})
            record=json.loads(p.read_text());record['payload']['rows']=[2];p.write_text(json.dumps(record))
            with self.assertRaises(ValueError):load(p,{'v':1})

    def make_registry(self, root):
        (root/'blackbox').mkdir()
        for name in ('features.py','domain.py','outcome_history.py'):shutil.copy2(ROOT/'blackbox'/name,root/'blackbox'/name)
        return publish({'model':'test'},{'donors':[]},{'test':True},root)

    def test_release_is_content_identified_and_existing_version_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rid=self.make_registry(root);before=(root/'artifacts/releases'/rid/'model.json').read_bytes()
            other=publish({'model':'changed'},{'donors':[]},{'test':True},root)
            self.assertNotEqual(rid,other)
            self.assertEqual((root/'artifacts/releases'/rid/'model.json').read_bytes(),before)

    def test_published_release_is_readable_by_container_user(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rid=self.make_registry(root)
            folder=root/'artifacts/releases'/rid
            if __import__('os').name!='nt':
                self.assertEqual(folder.stat().st_mode & 0o777,0o755)
                for file in folder.iterdir():self.assertEqual(file.stat().st_mode & 0o777,0o644)
            else:
                self.assertTrue(all(file.is_file() for file in folder.iterdir()))

    def test_sampler_tamper_invalidates_entire_release(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rid=self.make_registry(root)
            (root/'artifacts/releases'/rid/'answers.json').write_text('{"donors":[1]}')
            with self.assertRaises(ValueError):verify(rid,root)

    def test_feature_code_change_prevents_serving_old_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rid=self.make_registry(root)
            (root/'blackbox/features.py').write_text('different transform')
            with self.assertRaises(ValueError):verify(rid,root)

    def test_select_and_rollback_recover_exact_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=self.make_registry(root)
            second=publish({'model':'changed'},{'donors':[]},{'test':True},root)
            select(first,root=root);before=identity(root)
            select(second,root=root);self.assertNotEqual(before,identity(root))
            select(first,root=root);self.assertEqual(before,identity(root))

if __name__=='__main__':unittest.main()
