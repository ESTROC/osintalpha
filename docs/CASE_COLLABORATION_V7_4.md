# V7.4 — Case-scoped analyst collaboration

## Implemented
- Explicit grants and revocations of editor access to registered active analyst accounts.
- Case editors can participate in one authorized investigation without gaining access to unrelated cases.
- The case registry includes cases owned by or explicitly shared with an analyst.
- Case deletion and membership management remain owner/admin-only.
- Existing source, research and task endpoints use the central case access check.
- Task assignees may be case editors, owners or the administrator for that case.
- Membership changes are written to the audit log.
- Team UI shows owner, authorized editors, membership management controls.
- Automated tests cover isolation, unauthorized escalation, editor visibility, assignment, revocation and cascade deletion.

## Not yet enterprise collaboration
Editor access is coarse-grained, not read-only or per-action. Reports and conversation history need a separate privacy and retention policy before multi-company use. Formal approval workflows, invitations, external email notification and independent security testing remain incomplete. Never call this SSO/MFA-certified or a complete 95-issue solution.