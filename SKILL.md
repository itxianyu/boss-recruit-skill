---
name: boss-recruit-skill
description: Use when Codex, Claude, DeepSeek, or another agent needs a Boss Zhipin recruiting skill that can be triggered from natural-language hiring requests and then run a local Python workflow for resume collection, matching, and PDF or Excel output. Use for Boss直聘, Boss Zhipin, 招聘, 岗位筛选, 简历匹配, 职位分析, 投递建议, or MCP-based recruiting automation.
---

# Boss Recruit Skill

Use the `boss-zhipin` MCP server as the primary live data source when available. Use the bundled Python module when the agent needs to produce structured results or files.

This skill supports filtering by work address, age, work experience, salary range, and explicit job requirements in addition to the basic role, city, education, and skill filters.

## Preconditions

- If Python is not installed on the local machine, help the user install Python before attempting MCP setup or local skill execution.
- Confirm the `boss-zhipin` MCP server is enabled before relying on live data.
- If the local machine has not registered `boss-zhipin`, help the user register and enable it before continuing.
- If the MCP server is unavailable, say so clearly and continue with offline help such as resume targeting, JD analysis, message drafting, or screening rubric design.
- Read [references/boss-mcp-setup.md](references/boss-mcp-setup.md) when setup or authentication is incomplete.
- Use [boss_recruit_skill.py](boss_recruit_skill.py) when the agent needs to generate ranked matches, PDF summaries, or an Excel export.
- Use [scripts/bootstrap_python_env.ps1](scripts/bootstrap_python_env.ps1) when Python or required packages are missing.
- Use [scripts/register_boss_mcp.ps1](scripts/register_boss_mcp.ps1) to write the required `boss-zhipin` MCP configuration into the local Codex config file.

## Python entry points

- `BossRecruitSkill.prepare_execution(symptom_text="")`
- `BossRecruitSkill.search_and_generate(job_req)`
- `BossRecruitSkill.search_and_generate_from_text(request_text)`
- Example runner: [examples/run_skill.py](examples/run_skill.py)

Preferred usage:

1. Run `prepare_execution()` first.
2. If the returned status is not `ready`, follow the returned next actions instead of forcing the workflow to continue.
3. Extract hiring constraints from the user's natural-language request.
4. Build a `job_req` object with:
   - `title`
   - `skills`
   - `experience`
   - `city`
   - `education`
   - `work_address`
   - `max_age`
   - `salary_min_k`
   - `salary_max_k`
   - `job_requirements`
5. Call `search_and_generate(job_req)` when the fields are already known.
6. Call `search_and_generate_from_text(request_text)` when only a raw request is available.

Minimal example:

```python
from boss_recruit_skill import BossRecruitSkill

skill = BossRecruitSkill()
health = skill.prepare_execution()
if health["ready"]:
    result = skill.search_and_generate_from_text("帮我找上海 Python 后端开发，要求 3 年经验，30 岁以下，本科，25-30k，上班地址上海浦东，岗位要求 Python、Django、MySQL，生成 PDF 和 Excel")
```

## Workflow

1. Clarify the operating mode from the user request:
   - job seeker: find and compare roles, summarize requirements, tailor messages
   - recruiter: search candidates or openings, structure screening criteria, draft communication
   - analyst: summarize market signals such as title frequency, salary ranges, city distribution, and skill demand
2. Gather constraints before broad searches:
   - keyword or target role
   - city or remote preference
   - work address
   - age
   - salary range
   - experience level
   - industry, company stage, or company size
   - explicit job requirements
   - must-have and reject conditions
3. Run the narrowest MCP queries that can answer the request.
4. Normalize results into comparable fields:
   - title
   - company
   - city
   - salary
   - experience
   - education
   - financing or company size when available
   - key requirements
   - notable risks or ambiguities
5. Synthesize recommendations instead of dumping raw records.

## Python setup workflow

1. Check whether `python` or `py` is available locally.
2. If neither is available, help the user install Python first.
3. Run [scripts/bootstrap_python_env.ps1](scripts/bootstrap_python_env.ps1) from the skill root to:
   - install Python with `winget` when needed
   - confirm `pip` is available
   - install packages from `requirements.txt`
4. Only continue with MCP registration or skill execution after the Python environment is ready.

## MCP setup workflow

1. Check whether `boss-zhipin` is already registered in the local Codex MCP config.
2. If it is missing, ask the user for:
   - `COOKIE`
   - `BST`
3. Write the config by using [scripts/register_boss_mcp.ps1](scripts/register_boss_mcp.ps1).
4. Tell the user to restart the Codex session so the new MCP server can be loaded.
5. After restart, verify the MCP server state with `codex mcp list`.

## MCP loop handling

1. If Boss pages keep opening repeatedly, stop treating that as a normal retry case.
2. Treat maintenance pages, redirect loops, and repeated browser launches as MCP failure symptoms.
3. Temporarily disable the MCP entry by using [scripts/disable_boss_mcp.ps1](scripts/disable_boss_mcp.ps1).
4. Ask the user to refresh `COOKIE` and `BST`, then register the MCP again.
5. Until the MCP is stable, continue with offline analysis instead of reopening Boss pages.

## Known risks

- `mcp-boss-zp` is a third-party MCP wrapper, so browser behavior can change without notice.
- A valid Boss account does not guarantee MCP stability. The MCP may still hit deprecated pages, redirect loops, or blocked browser flows.
- `COOKIE` and `BST` can expire independently of the visible browser login state.
- When the MCP is unstable, prefer disabling it and falling back to offline analysis instead of repeatedly reopening Boss pages.

## Output rules

- Present shortlists as compact tables or bullet lists with one line per item.
- Separate facts from inference.
- Call out unknown fields instead of guessing.
- When ranking jobs or candidates, state the ranking criteria first.
- When drafting outreach or application messages, keep them brief, specific, and aligned with the role requirements.
- When file generation succeeds, return the generated file paths explicitly.

## Result schema

- All Python entry points return a stable top-level schema with:
  - `schema_version`
  - `result_type`
  - `status`
- Success results use:
  - `result_type: success`
  - `blocked: false`
- Blocked results use:
  - `result_type: blocked`
  - `blocked: true`
  - `reason`
  - `next_actions`
- Diagnostic results use:
  - `result_type: diagnostic`
  - `ready`
  - `blocked`
  - `next_actions`

## Common tasks

### Search and shortlist jobs

- Translate the user goal into explicit filters.
- Remove mismatches early: city, salary floor, stack mismatch, seniority mismatch, suspicious compensation, and low-information listings.
- Return the best matches with a short reason for each.

### Compare multiple opportunities

- Compare salary, growth potential, stack fit, work model, hiring signal quality, and requirement realism.
- Highlight tradeoffs rather than forcing a single winner when the comparison is mixed.

### Analyze a JD

- Extract hard requirements, soft preferences, hidden expectations, and likely interview focus.
- Identify resume gaps that matter and gaps that can be ignored.
- Suggest a tailored self-introduction, project emphasis, and outreach message.

### Draft recruiter or applicant messages

- Use the concrete role context, not generic templates.
- Keep first-contact messages concise.
- Avoid claims that are not supported by the user's experience or the job description.

## Failure handling

- If MCP calls fail, state whether the issue is authentication, server availability, or missing query constraints.
- If Python is missing locally, help the user install it instead of stopping at an import or command-not-found error.
- If `boss-zhipin` is not registered locally, help the user complete registration instead of stopping at an error.
- If `boss-zhipin` keeps opening browser pages or lands on a maintenance page, stop retrying, disable the MCP temporarily, and ask the user to refresh `COOKIE` and `BST`.
- Offer the fastest fallback path: refine the query, fix MCP setup, or switch to offline analysis.
- If the Python workflow is used without live Boss data, state that the output is based on the provided or fallback resume dataset.

## Reference

- Setup and authentication: [references/boss-mcp-setup.md](references/boss-mcp-setup.md)
