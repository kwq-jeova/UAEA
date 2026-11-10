"""Observation identity is append-only through the Source insertion API."""
from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from memory.sqlite_store import connect, initialize, insert_web_access_event, get_web_access_event, get_web_source


class WebAccessImmutabilityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / 'source.sqlite'
        self.c = connect(self.db)
        self.addCleanup(self.c.close)
        initialize(self.c)
        self.a = self.root / 'a.html'
        self.a.write_text('<p>Version one, fact 731.</p>')
        self.event = {'access_event_id': 'event-1', 'url': 'https://example.test/article',
                      'accessed_at': '2026-11-01T00:00:00Z', 'access_status': 'fetched',
                      'source_type': 'web_page', 'content_ref': str(self.a), 'http_status': 200,
                      'title': 'Original', 'excerpt': 'fact 731', 'metadata': {'origin': 'fixture'}}
        insert_web_access_event(self.c, self.event)
        self.c.commit()
        self.old = get_web_access_event(self.c, 'event-1')

    def test_duplicate_is_idempotent_without_rewinding_latest_source(self):
        b = self.root / 'b.html'; b.write_text('<p>Version two, fact 952.</p>')
        new = {**self.event, 'access_event_id': 'event-2', 'content_ref': str(b), 'excerpt': 'fact 952',
               'accessed_at': '2026-11-02T00:00:00Z'}
        insert_web_access_event(self.c, new)
        latest = get_web_source(self.c, self.old['web_source_id'])
        self.assertEqual(insert_web_access_event(self.c, deepcopy(self.event)), 'event-1')
        self.assertEqual(get_web_access_event(self.c, 'event-1'), self.old)
        self.assertEqual(get_web_source(self.c, self.old['web_source_id']), latest)
        self.assertNotEqual(get_web_access_event(self.c, 'event-2')['content_sha256'], self.old['content_sha256'])

    def test_same_id_cannot_change_identity_or_historical_metadata(self):
        for update in ({'url': 'https://different.test/'}, {'title': 'Corrected silently'},
                       {'accessed_at': '2026-11-04T00:00:00Z'}, {'excerpt': 'invented'},
                       {'metadata': {'origin': 'replaced'}}, {'access_status': 'failed'}):
            with self.subTest(update=update):
                with self.assertRaisesRegex(ValueError, 'immutable'):
                    insert_web_access_event(self.c, {**self.event, **update})
                self.assertEqual(get_web_access_event(self.c, 'event-1'), self.old)
        self.assertEqual(self.c.execute('SELECT count(*) FROM web_sources').fetchone()[0], 1)

    def test_changed_bytes_cannot_be_rehashed_under_old_id(self):
        self.a.write_text('<p>Changed in place.</p>')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            insert_web_access_event(self.c, self.event)
        self.assertEqual(get_web_access_event(self.c, 'event-1'), self.old)

    def test_insert_failure_rolls_back_latest_pointer_but_not_prior_caller_work(self):
        self.c.execute("CREATE TABLE caller_work(value TEXT)")
        self.c.execute("INSERT INTO caller_work VALUES ('retained')")
        self.c.execute("""CREATE TEMP TRIGGER reject_access BEFORE INSERT ON web_access_events
                          WHEN NEW.access_event_id='event-2'
                          BEGIN SELECT RAISE(ABORT, 'deliberate failure'); END""")
        latest = get_web_source(self.c, self.old['web_source_id'])
        with self.assertRaises(sqlite3.IntegrityError):
            insert_web_access_event(self.c, {**self.event, 'access_event_id': 'event-2', 'title': 'new'})
        self.assertEqual(get_web_source(self.c, self.old['web_source_id']), latest)
        self.assertIsNone(get_web_access_event(self.c, 'event-2'))
        self.assertEqual(self.c.execute('SELECT value FROM caller_work').fetchone()[0], 'retained')

    def test_caller_controls_commit(self):
        insert_web_access_event(self.c, {**self.event, 'access_event_id': 'event-2'})
        reader = connect(self.db)
        self.addCleanup(reader.close)
        self.assertIsNone(get_web_access_event(reader, 'event-2'))
        self.c.commit()
        self.assertIsNotNone(get_web_access_event(reader, 'event-2'))


if __name__ == '__main__':
    unittest.main()
