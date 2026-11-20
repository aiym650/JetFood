from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase


class MergeHistoryRepairTests(TestCase):
    def test_audit_is_read_only_and_apply_only_records_noop_merge(self):
        recorder = MigrationRecorder(connection)
        key = ('orders', '0009_merge_20261113_1340')
        recorder.record_unapplied(*key)
        output = StringIO()
        call_command('repair_merge_history', stdout=output)
        self.assertIn('Read-only audit', output.getvalue())
        self.assertNotIn(key, recorder.applied_migrations())
        call_command('repair_merge_history', apply=True, stdout=StringIO())
        self.assertIn(key, recorder.applied_migrations())
        MigrationLoader(connection).check_consistent_history(connection)

    def test_repair_refuses_missing_migration_with_operations(self):
        MigrationRecorder(connection).record_unapplied('orders', '0013_backfill_categories_and_totals')
        with self.assertRaises(CommandError):
            call_command('repair_merge_history', apply=True, stdout=StringIO())
