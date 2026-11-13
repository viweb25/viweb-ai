# Starter cleanup and migration map

All original non-placeholder source/configuration was preserved. Empty .gitkeep files
were removed in favour of useful code or responsibility READMEs. Original Office files
outside the workspace are untouched. Environment-owned .git/.agents/.codex/.aws were untouched.

| Previous path | Active replacement |
| --- | --- |
| backend/ | services/api/ |
| edge/ | services/edge-agent/ |
| packages/vi_ml/vi_ml/ | ai/vi_ml/ |
| packages/vi_ml/tests/ | ai/tests/ |
| labview/ | packages/labview/ |
| contracts/ | packages/schemas/ |
| docker-compose.local.yml | infra/docker-compose.yml |
| Bitbucket/Azure deployment stub | GitHub checks; deployment remains unconfigured |
| .claude/commands | Archived; new role guides replace obsolete commands |

`docs/archive/starter/` retains original README, CLAUDE instructions, Makefile, .env
example, Compose, Bitbucket pipeline, Azure deploy script, plugin base/template and
old job/result schemas. They are historical evidence, not runnable commands or active
instructions. A future cleanup PR may remove this archive once the team has reviewed it.

No real Git diff/commit could be produced: the supplied .git is environment-owned and
not a usable repository. Changes were made only in the provided workspace.
