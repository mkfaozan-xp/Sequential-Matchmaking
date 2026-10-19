"""Atomic JSON and an append-only, leased SQLite experiment ledger."""
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{uuid.uuid4().hex}.tmp')
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class RunBusy(RuntimeError):
    pass


class LostLease(RuntimeError):
    pass


class Ledger:
    """One active owner per run. Expired attempts remain in the audit history."""

    def __init__(self, path, lease_seconds=120, clock=time.time):
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 2, 3):
            self.db.close()
            raise ValueError('Legacy ledger: archive it and use a new v0.2 ledger path')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, config TEXT NOT NULL,
                status TEXT NOT NULL, active_attempt TEXT,
                result TEXT, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
                owner TEXT NOT NULL, status TEXT NOT NULL, started REAL NOT NULL,
                heartbeat REAL NOT NULL, lease_until REAL NOT NULL,
                completed REAL, result TEXT, error TEXT);
        ''')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            columns = {r[1] for r in self.db.execute('PRAGMA table_info(attempts)')}
            if 'guard_version' not in columns:
                self.db.execute('ALTER TABLE attempts ADD COLUMN guard_version INTEGER NOT NULL DEFAULT 0')
            self.db.execute('PRAGMA user_version=3')
            self.db.commit()
        except BaseException:
            self.db.rollback();self.db.close();raise
        self.clock = clock
        self.lease_seconds = lease_seconds
        self.owner = uuid.uuid4().hex
        self.claims = {}
        self.guard_directory = Path(str(path) + '.owners')
        self.guard_directory.mkdir(parents=True, exist_ok=True)
        self.guard = WorkflowLock(self.guard_directory / (self.owner + '.lock'))
        self.guard.__enter__()

    def owner_stopped(self, owner, guard_version):
        """An abandoned OS lock proves death without PID reuse or namespace ambiguity.

        Unknown/legacy owners retain lease recovery. Never unlink lock files: that
        could create two independently locked inodes for the same owner.
        """
        path = self.guard_directory / (owner + '.lock')
        if guard_version != 1 or not path.is_file():
            return False
        try:
            with WorkflowLock(path):
                return True
        except RunBusy:
            return False

    def claim(self, config):
        key, now = digest(config), self.clock()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute(
                'SELECT status,active_attempt,result FROM runs WHERE run_id=?', (key,)
            ).fetchone()
            if row and row[0] == 'completed':
                self.db.commit()
                return key, json.loads(row[2])
            if row and row[0] == 'running':
                attempt = self.db.execute(
                    'SELECT lease_until,owner,guard_version FROM attempts WHERE attempt_id=?', (row[1],)
                ).fetchone()
                stopped = bool(attempt and self.owner_stopped(attempt[1], attempt[2]))
                if attempt and attempt[0] > now and not stopped:
                    raise RunBusy('Another worker owns this episode; wait for its lease or use its result')
                self.db.execute(
                    'UPDATE attempts SET status=?,completed=?,error=? WHERE attempt_id=?',
                    ('interrupted', now, 'owner OS lock released' if stopped else 'owner lease expired', row[1]),
                )
            attempt_id = uuid.uuid4().hex
            if row:
                self.db.execute(
                    'UPDATE runs SET status=?,active_attempt=?,result=NULL,updated=? WHERE run_id=?',
                    ('running', attempt_id, now, key),
                )
            else:
                self.db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',
                                (key, canonical(config), 'running', attempt_id, None, now))
            self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                            (attempt_id, key, self.owner, 'running', now, now,
                             now + self.lease_seconds, None, None, None, 1))
            self.db.commit()
            self.claims[key] = attempt_id
            return key, None
        except BaseException:
            self.db.rollback()
            raise

    def heartbeat(self, key):
        now = self.clock()
        with self.db:
            cursor = self.db.execute('''UPDATE attempts SET heartbeat=?,lease_until=?
                WHERE attempt_id=? AND owner=? AND status='running' AND lease_until>=?
                AND EXISTS (SELECT 1 FROM runs WHERE run_id=? AND active_attempt=attempts.attempt_id)''',
                (now, now + self.lease_seconds, self.claims.get(key), self.owner, now, key))
            if cursor.rowcount != 1:
                raise LostLease('Episode owner lost its lease')

    def finish(self, key, result):
        now, attempt_id = self.clock(), self.claims.get(key)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('''SELECT a.owner,a.status,a.lease_until,r.active_attempt
                FROM attempts a JOIN runs r ON a.run_id=r.run_id
                WHERE a.attempt_id=? AND r.run_id=?''', (attempt_id, key)).fetchone()
            if not row or row != (self.owner, 'running', row[2], attempt_id) or row[2] < now:
                raise LostLease('Stale owner cannot commit this episode')
            status = 'completed' if result['valid'] else 'failed'
            payload = canonical(result)
            self.db.execute('UPDATE attempts SET status=?,completed=?,result=?,error=? WHERE attempt_id=?',
                            (status, now, payload, result.get('error'), attempt_id))
            self.db.execute('UPDATE runs SET status=?,result=?,updated=? WHERE run_id=?',
                            (status, payload, now, key))
            self.db.commit()
            self.claims.pop(key, None)
        except BaseException:
            self.db.rollback()
            raise

    def audit(self):
        self.db.row_factory = sqlite3.Row
        rows = [dict(row) for row in self.db.execute(
            'SELECT attempt_id,run_id,status,started,completed,error FROM attempts ORDER BY started,attempt_id')]
        self.db.row_factory = None
        return rows

    def close(self):
        now = self.clock()
        with self.db:
            for key, attempt_id in self.claims.items():
                self.db.execute("UPDATE attempts SET status='interrupted',completed=?,error=? WHERE attempt_id=? AND owner=? AND status='running'",
                                (now, 'owner closed before completion', attempt_id, self.owner))
                self.db.execute("UPDATE runs SET status='interrupted',updated=? WHERE run_id=? AND active_attempt=? AND status='running'",
                                (now, key, attempt_id))
        self.claims.clear()
        self.db.close()
        self.guard.__exit__()


class WorkflowLock:
    """An OS-held single-writer lock, released automatically if the supervisor dies."""

    def __init__(self,path):
        self.path=Path(path)
        self.stream=None

    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.stream=self.path.open('a+b')
        self.stream.seek(0,os.SEEK_END)
        if self.stream.tell()==0:
            self.stream.write(b'\0');self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close();self.stream=None
            raise RunBusy('Another workflow owns this results directory') from error
        return self

    def __exit__(self,*_):
        if self.stream is None:return
        try:
            self.stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
        finally:
            self.stream.close();self.stream=None
