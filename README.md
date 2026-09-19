# career-ops

Open-source AI job search that runs locally in your AI coding CLI. No
servers, no accounts, no data leaving your machine except the web requests
needed to read job postings you point it at.

career-ops is a [Claude Code plugin](https://code.claude.com/docs/en/plugins)
skill that turns your CLI into a job-search assistant:

- **Scan** job portals and career pages (or a pasted list of listing URLs)
  for roles matching your criteria.
- **Evaluate** every listing into a structured, eight-section (A–H) report —
  role summary, requirements match, comp, company signals, location/work
  arrangement, growth trajectory, application effort, and red flags — ending
  in an overall **1–5 fit score** and a recommendation.
- **Tailor** your CV to each role you decide to pursue, without inventing
  experience you don't have.
- **Track** every application in a single local CSV: status, follow-up
  dates, and links to the report and tailored CV for that role.

Everything career-ops produces (your resume, evaluation reports, and the
application tracker) is written as plain files inside a `career-ops/`
directory in *your own project* — never inside this plugin's install
directory.

## Install

Add this repo as a plugin marketplace, then install the plugin:

```
/plugin marketplace add <owner>/career-ops
/plugin install career-ops
```

## Use

From any project, just ask, for example:

- "Find me senior backend roles, remote, US timezone, no on-call-heavy
  teams."
- "Evaluate this listing: <url>"
- "Score these three postings and tell me which to apply to."
- "Tailor my resume for the Example Co posting."
- "What's the status of my applications? Anything I need to follow up on?"

The first time you use it in a project, it'll ask for your base resume and
set up the `career-ops/` workspace. See
[`skills/career-ops/SKILL.md`](skills/career-ops/SKILL.md) for the full
workflow and rubric.

## License

MIT — see [LICENSE](LICENSE).
