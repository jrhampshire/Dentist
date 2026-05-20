"""
Management command: setup_rls

Applies all Row Level Security (RLS) policies to PostgreSQL tables.
This command is idempotent — safe to run multiple times.

Usage:
    python manage.py setup_rls --settings=config.settings.dev

Run this after initial migrations to enable multi-tenant isolation.
"""

from django.core.management.base import BaseCommand
from django.db import connection

# All 16 tables that need RLS policies
# Format: (table_name, isolation_policy_name, additional_policies)
TABLES = [
    # Core tenant tables
    ("clinics", "clinic_isolation", []),
    ("onboarding_steps", "onboarding_isolation", []),
    # Auth tables
    (
        "users",
        "user_isolation",
        [
            # Admins see all users in their clinic; others see only themselves
            """
        CREATE POLICY user_role_access ON users
        FOR SELECT
        USING (
            clinic_id = current_setting('app.current_clinic_id')::uuid
            AND (
                current_setting('app.current_user_role') = 'admin'
                OR id = current_setting('app.current_user_id')::uuid
            )
        );
        """,
        ],
    ),
    ("refresh_tokens", "refresh_token_isolation", []),
    # Patient management tables
    ("patients", "patient_isolation", []),
    (
        "clinical_notes",
        "notes_isolation",
        [
            # Dentists can only see notes for their own patients via appointments
            """
        CREATE POLICY notes_dentist_access ON clinical_notes
        FOR SELECT
        USING (
            current_setting('app.current_user_role') IN ('admin', 'dentista')
        );
        """,
        ],
    ),
    ("patient_consents", "consent_isolation", []),
    # Appointment tables
    ("appointment_types", "appt_type_isolation", []),
    ("appointments", "appointment_isolation", []),
    ("schedule_slots", "schedule_isolation", []),
    # Invoicing tables
    ("fiscal_configs", "fiscal_isolation", []),
    ("invoices", "invoice_isolation", []),
    # Notification tables
    ("notification_logs", "notif_isolation", []),
    ("whatsapp_webhooks", "webhook_isolation", []),
    # Inventory tables (Batch 8)
    ("inventory_items", "inventory_isolation", []),
    ("inventory_movements", "movement_isolation", []),
]

# Audit log table — special: enable RLS but also add DB triggers for immutability
AUDIT_TABLE = "audit_logs"


class Command(BaseCommand):
    help = "Apply Row Level Security (RLS) policies to all PostgreSQL tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print SQL without executing.",
        )
        parser.add_argument(
            "--drop-first",
            action="store_true",
            help="Drop existing policies before creating new ones.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        drop_first = options["drop_first"]

        self.stdout.write(self.style.SUCCESS("Starting RLS policy setup..."))

        with connection.cursor() as cursor:
            for table_name, policy_name, extra_policies in TABLES:
                self._apply_rls_for_table(
                    cursor, table_name, policy_name, extra_policies, dry_run, drop_first
                )

            # Special handling for audit_logs (immutability triggers)
            self._setup_audit_log_protection(cursor, dry_run, drop_first)

            # Special trigger for signed clinical notes
            self._setup_signed_notes_protection(cursor, dry_run, drop_first)

        self.stdout.write(
            self.style.SUCCESS("RLS policies applied successfully to all 16 tables.")
        )

    def _apply_rls_for_table(
        self, cursor, table_name, policy_name, extra_policies, dry_run, drop_first
    ):
        """Apply RLS to a single table."""
        self.stdout.write(f"  Configuring table: {table_name}")

        # Enable RLS
        sql_enable = f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"
        self._execute(cursor, sql_enable, dry_run)

        # Drop existing policy if --drop-first
        if drop_first:
            sql_drop = f"DROP POLICY IF EXISTS {policy_name} ON {table_name};"
            self._execute(cursor, sql_drop, dry_run)

        # Create isolation policy
        # Use clinic_id for most tables; special handling for clinics table
        if table_name == "clinics":
            policy_sql = (
                f"CREATE POLICY {policy_name} ON {table_name} "
                f"FOR ALL USING (id = current_setting('app.current_clinic_id')::uuid);"
            )
        else:
            policy_sql = (
                f"CREATE POLICY {policy_name} ON {table_name} "
                f"FOR ALL USING (clinic_id = current_setting('app.current_clinic_id')::uuid);"
            )
        self._execute(cursor, policy_sql, dry_run)

        # Apply extra policies
        for extra_sql in extra_policies:
            if drop_first:
                # Extract policy name from the CREATE POLICY statement
                for line in extra_sql.strip().split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("CREATE POLICY"):
                        parts = stripped.split()
                        if len(parts) >= 4:
                            extra_policy_name = parts[2]
                            drop_extra = f"DROP POLICY IF EXISTS {extra_policy_name} ON {table_name};"
                            self._execute(cursor, drop_extra, dry_run)
                        break
            self._execute(cursor, extra_sql, dry_run)

    def _setup_audit_log_protection(self, cursor, dry_run, drop_first):
        """Set up DB triggers to prevent UPDATE/DELETE on audit_logs."""
        self.stdout.write("  Configuring audit_logs immutability triggers...")

        # Enable RLS
        sql_enable = f"ALTER TABLE {AUDIT_TABLE} ENABLE ROW LEVEL SECURITY;"
        self._execute(cursor, sql_enable, dry_run)

        # Drop existing policies if --drop-first
        if drop_first:
            self._execute(
                cursor,
                f"DROP POLICY IF EXISTS audit_isolation ON {AUDIT_TABLE};",
                dry_run,
            )
            self._execute(
                cursor,
                f"DROP TRIGGER IF EXISTS prevent_audit_update ON {AUDIT_TABLE};",
                dry_run,
            )
            self._execute(
                cursor,
                f"DROP TRIGGER IF EXISTS prevent_audit_delete ON {AUDIT_TABLE};",
                dry_run,
            )
            self._execute(
                cursor, f"DROP FUNCTION IF EXISTS prevent_audit_update();", dry_run
            )
            self._execute(
                cursor, f"DROP FUNCTION IF EXISTS prevent_audit_delete();", dry_run
            )

        # RLS isolation policy
        policy_sql = (
            f"CREATE POLICY audit_isolation ON {AUDIT_TABLE} "
            f"FOR ALL USING (clinic_id = current_setting('app.current_clinic_id')::uuid);"
        )
        self._execute(cursor, policy_sql, dry_run)

        # Trigger: prevent UPDATE on audit_logs
        trigger_update = f"""
        CREATE OR REPLACE FUNCTION prevent_audit_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'AuditLog entries are immutable. UPDATE is not allowed.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_audit_update
        BEFORE UPDATE ON {AUDIT_TABLE}
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_update();
        """
        self._execute(cursor, trigger_update, dry_run)

        # Trigger: prevent DELETE on audit_logs
        trigger_delete = f"""
        CREATE OR REPLACE FUNCTION prevent_audit_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'AuditLog entries are immutable. DELETE is not allowed.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_audit_delete
        BEFORE DELETE ON {AUDIT_TABLE}
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_delete();
        """
        self._execute(cursor, trigger_delete, dry_run)

    def _setup_signed_notes_protection(self, cursor, dry_run, drop_first):
        """Set up DB trigger to prevent UPDATE/DELETE on signed clinical notes."""
        self.stdout.write("  Configuring signed clinical notes protection...")

        if drop_first:
            self._execute(
                cursor,
                "DROP TRIGGER IF EXISTS prevent_signed_note_update ON clinical_notes;",
                dry_run,
            )
            self._execute(
                cursor,
                "DROP TRIGGER IF EXISTS prevent_signed_note_delete ON clinical_notes;",
                dry_run,
            )
            self._execute(
                cursor, "DROP FUNCTION IF EXISTS prevent_signed_note_update();", dry_run
            )
            self._execute(
                cursor, "DROP FUNCTION IF EXISTS prevent_signed_note_delete();", dry_run
            )

        # Trigger: prevent UPDATE on signed clinical notes
        trigger_update = """
        CREATE OR REPLACE FUNCTION prevent_signed_note_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.is_signed = true THEN
                RAISE EXCEPTION 'Cannot update a signed clinical note. Create a new note instead.';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_signed_note_update
        BEFORE UPDATE ON clinical_notes
        FOR EACH ROW
        EXECUTE FUNCTION prevent_signed_note_update();
        """
        self._execute(cursor, trigger_update, dry_run)

        # Trigger: prevent DELETE on signed clinical notes
        trigger_delete = """
        CREATE OR REPLACE FUNCTION prevent_signed_note_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.is_signed = true THEN
                RAISE EXCEPTION 'Cannot delete a signed clinical note.';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_signed_note_delete
        BEFORE DELETE ON clinical_notes
        FOR EACH ROW
        EXECUTE FUNCTION prevent_signed_note_delete();
        """
        self._execute(cursor, trigger_delete, dry_run)

    @staticmethod
    def _execute(cursor, sql, dry_run):
        """Execute SQL or print it if dry_run."""
        sql_stripped = sql.strip()
        if dry_run:
            print(f"  SQL: {sql_stripped}")
        else:
            try:
                cursor.execute(sql_stripped)
            except Exception as exc:
                # Some policies may already exist — that's OK for idempotency
                if "already exists" in str(exc).lower():
                    pass  # Policy already exists, skip
                else:
                    raise
