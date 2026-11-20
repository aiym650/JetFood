from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = 'Audit missing, operation-free merge records required by already applied migrations. Read-only unless --apply is specified.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Record only verified missing no-op merges. Back up the database first.')

    def handle(self, *args, **options):
        loader = MigrationLoader(connection)
        applied = set(loader.applied_migrations)
        missing = set()

        def visit(key):
            if key in applied or key in missing:
                return
            migration = loader.disk_migrations[key]
            if migration.operations or len(migration.dependencies) < 2:
                raise CommandError(f'{key[0]}.{key[1]} is not an operation-free merge. Refusing automatic history repair.')
            for parent in loader.graph.node_map[key].parents:
                visit(parent.key)
            missing.add(key)

        for key in applied:
            if key in loader.graph.node_map:
                for parent in loader.graph.node_map[key].parents:
                    visit(parent.key)
        if not missing:
            self.stdout.write('No missing merge records found.')
            return
        ordered = []
        for leaf in sorted(missing):
            for key in loader.graph.forwards_plan(leaf):
                if key in missing and key not in ordered:
                    ordered.append(key)
        for app, name in ordered:
            self.stdout.write(f'Missing no-op merge: {app}.{name}')
        if not options['apply']:
            self.stdout.write('Read-only audit. Back up the database, then rerun with --apply to record these no-op merges.')
            return
        with transaction.atomic():
            recorder = MigrationRecorder(connection)
            for app, name in ordered:
                recorder.record_applied(app, name)
        self.stdout.write(self.style.SUCCESS(f'Recorded {len(ordered)} no-op merge migrations. No application data or schema was changed.'))
