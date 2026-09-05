# Deployment Backup And Restore Drill

1. Confirm the stack is in MOCK research mode and order routing is disabled.
2. Call the backup endpoint as a risk manager or administrator.
3. Record the backup ID, SHA-256, size, table count, and integrity result.
4. Call the restore-drill endpoint as an administrator using that exact artifact.
5. Verify hash equality, SQLite integrity, table count, and important row counts.
6. Confirm `production_database_modified=false`.
7. Never replace the production database automatically from a drill artifact.
