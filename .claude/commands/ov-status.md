# /ov-status -- OpenViking Status Check

Quick health check for the OpenViking context database.

## Steps

1. **Health check**: Run `ov health` and report pass/fail.

2. **Server status**: If healthy, run `ov status` for server details (uptime, resource count).

3. **Registered resources**: Run `ov ls viking://agent-orchestrator/ -s` to list all registered resources.

4. **Summary table**: Print a table with columns: URI, Type, Status.

5. **Troubleshooting**: If OV is not running:
   - Suggest: `bash scripts/ov-serve.sh start`
   - Suggest: `bash scripts/ov-bootstrap.sh` to register resources
   - Note: OV is optional -- all pipeline features work without it via file-scan fallback.

## Arguments

- `$ARGUMENTS` — Optional: a specific `viking://` URI to inspect in detail.
