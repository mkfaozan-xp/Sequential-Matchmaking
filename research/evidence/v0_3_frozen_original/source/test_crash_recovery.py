"""Real process-death recovery, plus backward-compatible lease safety."""
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from blackbox.storage import Ledger, RunBusy, WorkflowLock


class CrashRecoveryTests(unittest.TestCase):
    def child(self, program, path):
        process=subprocess.Popen([sys.executable,'-u','-c',program,str(path)],stdout=subprocess.PIPE,text=True)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        self.assertEqual(process.stdout.readline().strip(),'ready')
        return process

    def test_hard_killed_episode_reclaimed_before_lease_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.sqlite'
            process=self.child("from blackbox.storage import Ledger; import sys,time; l=Ledger(sys.argv[1]); l.claim({'seed':1}); print('ready',flush=True); time.sleep(60)",path)
            ledger=Ledger(path)
            with self.assertRaises(RunBusy):ledger.claim({'seed':1})
            process.kill();process.wait(timeout=5);process.stdout.close()
            self.assertGreater(ledger.db.execute('SELECT lease_until FROM attempts').fetchone()[0],time.time())
            key,_=ledger.claim({'seed':1});ledger.finish(key,{'valid':True})
            attempts=ledger.audit()
            self.assertEqual([a['status'] for a in attempts],['interrupted','completed'])
            self.assertEqual(attempts[0]['error'],'owner OS lock released')
            ledger.close()

    def test_supervisor_lock_released_on_hard_kill(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'workflow.lock'
            process=self.child("from blackbox.storage import WorkflowLock; import sys,time; l=WorkflowLock(sys.argv[1]); l.__enter__(); print('ready',flush=True); time.sleep(60)",path)
            with self.assertRaises(RunBusy):
                with WorkflowLock(path):pass
            process.kill();process.wait(timeout=5);process.stdout.close()
            with WorkflowLock(path):pass

    def test_legacy_attempt_keeps_lease_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.sqlite';first=Ledger(path);second=Ledger(path)
            first.claim({'seed':1})
            # Version-2 owners have no guard protocol; absence must not imply death.
            first.db.execute('UPDATE attempts SET guard_version=0');first.db.commit()
            with self.assertRaises(RunBusy):second.claim({'seed':1})
            first.close();second.close()

    def test_version_two_ledger_migration_preserves_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.sqlite';old=Ledger(path)
            key,_=old.claim({'seed':1});old.finish(key,{'valid':True,'score':3});old.close()
            import sqlite3
            db=sqlite3.connect(path);db.execute('ALTER TABLE attempts DROP COLUMN guard_version')
            db.execute('PRAGMA user_version=2');db.commit();db.close()
            migrated=Ledger(path)
            self.assertEqual(migrated.claim({'seed':1})[1]['score'],3)
            self.assertEqual(len(migrated.audit()),1)
            self.assertEqual(migrated.db.execute('PRAGMA user_version').fetchone()[0],3)
            migrated.close()

if __name__=='__main__':unittest.main()
