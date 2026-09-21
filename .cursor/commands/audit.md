Run the `security-auditor` subagent to perform a security review of recent feature work.

Ask it to:
1. Scan modified files for hardcoded secrets.
2. Verify authentication guards on new routes.
3. Confirm `.env` handling and `.gitignore` coverage.
4. Report findings as a numbered list with severity: LOW / MEDIUM / HIGH.
5. Do not modify files.
