Review the changes on the current branch compared to main (`git diff main...HEAD`).
Check strictly: correctness, organization isolation (org_id), security, error handling, the rule that a missing AI
result is never PASS, backward-compatible migrations, contract changes, performance, missing tests.
Output two lists: MUST FIX and NICE TO HAVE, each with file:line and a suggested fix.
