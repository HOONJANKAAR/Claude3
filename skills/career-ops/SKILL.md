---
description: Use when the user wants to search for jobs, scan job portals or listing pages/URLs, evaluate a job posting's fit, tailor a CV/resume to a specific role, or track job applications. Triggers on requests like "find me jobs", "should I apply to this posting", "score this job listing", "tailor my resume for this role", or "update my application tracker".
allowed-tools: WebSearch WebFetch Read Write Edit Bash Glob Grep
---

# career-ops: local AI job search

career-ops turns this CLI into a private job-search assistant. Nothing leaves
the user's machine except the web requests needed to read job postings. All
state (the CV, evaluation reports, and the application tracker) lives as
plain files in the user's own working directory — never in this plugin's
source tree.

Run the phases below in order the first time a user engages career-ops in a
project; on later runs, jump straight to whichever phase they asked for.

## Workspace layout

Create/use this layout inside the user's current project (or ask where to
put it if the project already has an unrelated structure):

```
career-ops/
├── cv/
│   ├── base-resume.md          # the user's master resume (source of truth)
│   └── tailored/                # one tailored copy per application
│       └── <company>-<role-slug>.md
├── reports/
│   └── <company>-<role-slug>-<yyyy-mm-dd>.md   # one evaluation report per listing
└── applications.csv             # the application tracker (single file)
```

If `career-ops/` doesn't exist yet, create it, copy
`templates/applications-tracker.csv` from this skill into
`career-ops/applications.csv`, and ask the user for their base resume (a
pasted CV, an existing file to import, or an interview to draft one from) to
seed `career-ops/cv/base-resume.md`.

## Phase 1 — Intake

Before scanning anything, confirm with the user (skip questions they've
already answered in their request):
- Target role(s)/titles and seniority
- Location(s) or remote/hybrid/on-site preference
- Must-have constraints (visa sponsorship, salary floor, tech stack, industry
  to avoid, etc.)
- Which portals/sources to use (e.g. company career pages, LinkedIn, Indeed,
  Greenhouse/Lever boards, a pasted list of URLs). If the Indeed MCP tools
  (`mcp__Indeed__search_jobs`, `get_job_details`, `get_company_data`) are
  available in this session, prefer them over scraping for Indeed results.

## Phase 2 — Scan

For each source:
- If it's a search portal, use `WebSearch`/the Indeed MCP tools with the
  intake criteria to find candidate listings.
- If it's a specific URL or list of URLs, fetch each with `WebFetch`.
- Deduplicate by company + role + location.
- Skip anything that plainly fails a hard constraint from Phase 1 before
  spending effort evaluating it.

Keep a short running list (company, role, URL) in your response as you go so
the user can see progress on longer scans.

## Phase 3 — Evaluate (the A–H report)

For every listing that passes the Phase 2 filter, write one report to
`career-ops/reports/<company>-<role-slug>-<yyyy-mm-dd>.md` using
`templates/evaluation-report.md` from this skill as the structure. The
report has eight lettered sections plus an overall score:

- **A — Role Summary**: what the job actually is, in plain language (not
  copy-pasted from the posting).
- **B — Requirements Match**: line up the posting's must-haves/nice-to-haves
  against the user's base resume; call out real gaps, not just keyword
  overlap.
- **C — Compensation & Benefits**: posted range if given, market estimate if
  not (say clearly which), equity/bonus/benefits notes.
- **D — Company & Culture Signals**: what's verifiable (funding stage, size,
  recent news, glassdoor/review signal if fetched) vs. what's marketing copy.
- **E — Location & Work Arrangement**: remote/hybrid/on-site, timezone, and
  relocation/visa implications against the user's constraints.
- **F — Growth & Trajectory**: what this role plausibly leads to next, and
  whether it's a lateral move, a step up, or a step down for the user.
- **G — Application Effort & Process**: what applying requires (assessment,
  number of rounds, take-home, referral needed) and how to apply.
- **H — Red Flags & Risks**: anything concerning — vague scope, unusually
  broad requirements for the level, warning signs in reviews, ghost-job
  indicators (reposted for months, generic recruiter-spam phrasing).

Then give an **Overall Fit Score: N/5** (1 = don't apply, 5 = apply
immediately) with one sentence justifying the number, and a
**Recommendation**: `Apply`, `Maybe (needs more info)`, or `Skip`.

Be honest and specific in each section — a report that just restates the job
ad is useless to the user. Cite the source URL at the top of every report.

## Phase 4 — Rank & present

After evaluating a batch, present a ranked summary table (score, company,
role, recommendation, report path) sorted by score descending, and ask which
ones the user wants to move forward with. Don't tailor a CV or log an
application for anything the user hasn't confirmed.

## Phase 5 — Tailor the CV

For each listing the user wants to apply to:
1. Read `career-ops/cv/base-resume.md` and the matching evaluation report
   (section B already has the gap analysis — reuse it).
2. Produce a tailored version at
   `career-ops/cv/tailored/<company>-<role-slug>.md`: reorder/reweight real
   experience to match the posting's priorities, mirror its terminology
   where truthful, and tighten the summary line for this specific role.
3. Never fabricate experience, tools, titles, or dates that aren't in the
   base resume. Tailoring is emphasis and framing, not invention.
4. Use `templates/cv-tailoring-guide.md` in this skill for the specific
   do/don't rules (ATS formatting, quantification, length).
5. If the user wants a `.docx`/`.pdf` output instead of Markdown, use the
   appropriate document-generation skill/tool available in this environment
   to convert the tailored Markdown — don't hand-roll document formats here.

## Phase 6 — Track applications

`career-ops/applications.csv` is the single source of truth for pipeline
state. Columns (see `templates/applications-tracker.csv`):

```
date_added,company,role,location,score,status,url,report_path,cv_path,next_action,next_action_date,notes
```

- When the user confirms they're applying to a listing, append a row (status
  `applied`, `date_added` = today, links to the report and tailored CV).
- When the user reports a status change (screen scheduled, rejected, offer,
  ghosted), update that row's `status`, `next_action`, and
  `next_action_date` rather than adding a new row.
- On request, summarize the tracker (counts by status, anything with a
  `next_action_date` in the past that needs follow-up).
- Read and write this file with plain CSV edits — don't introduce a database
  or reformat columns the user didn't ask to change.

## Ground rules

- Only fetch publicly accessible pages; never try to bypass a login wall or
  paywall to read a listing.
- Never invent salary data, company facts, or review scores — mark estimates
  as estimates.
- Never fabricate resume content in Phase 5.
- Keep all state in the user's project under `career-ops/`, not in this
  plugin's installation directory.
