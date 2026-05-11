---
name: boss-recruit-skill
description: Use when Codex needs to work with Boss Zhipin hiring or job-search workflows through the `boss-zhipin` MCP server, including searching positions, filtering results, comparing jobs, extracting salary and requirement signals, drafting outreach or follow-up messages, and organizing candidate or opportunity review. Use for requests involving Boss直聘, Boss Zhipin, 招聘, 岗位筛选, 职位分析, 投递建议, or MCP-based recruiting automation.
---

# Boss Recruit Skill

Use the `boss-zhipin` MCP server as the primary data source when the user asks for live Boss Zhipin information.

## Preconditions

- Confirm the `boss-zhipin` MCP server is enabled before relying on live data.
- If the MCP server is unavailable, say so clearly and continue with offline help such as resume targeting, JD analysis, message drafting, or screening rubric design.
- Read [references/boss-mcp-setup.md](references/boss-mcp-setup.md) when setup or authentication is incomplete.

## Workflow

1. Clarify the operating mode from the user request:
   - job seeker: find and compare roles, summarize requirements, tailor messages
   - recruiter: search candidates or openings, structure screening criteria, draft communication
   - analyst: summarize market signals such as title frequency, salary ranges, city distribution, and skill demand
2. Gather constraints before broad searches:
   - keyword or target role
   - city or remote preference
   - salary range
   - experience level
   - industry, company stage, or company size
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

## Output rules

- Present shortlists as compact tables or bullet lists with one line per item.
- Separate facts from inference.
- Call out unknown fields instead of guessing.
- When ranking jobs or candidates, state the ranking criteria first.
- When drafting outreach or application messages, keep them brief, specific, and aligned with the role requirements.

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
- Offer the fastest fallback path: refine the query, fix MCP setup, or switch to offline analysis.

## Reference

- Setup and authentication: [references/boss-mcp-setup.md](references/boss-mcp-setup.md)
