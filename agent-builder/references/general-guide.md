# General Agent Guide

## Output
- Lead with results, not process
- Save deliverables to `output/`
- Structure output with clear headers

## Working With Skills
1. `read_file` a skill's SKILL.md for instructions before using it
2. Follow the skill's documented patterns
3. Report errors clearly with what failed and alternatives

## Working With Scripts
1. Read a script before running it to understand its interface
2. Run via `bash("python agents/{your-name}/scripts/script_name.py [args]")`
3. Prefer scripts over generating equivalent code — they're deterministic

## Memory
After each run, update `memory/MEMORY.md` with:
- Approaches that worked and why
- API quirks or gotchas discovered
- Thresholds and baselines for comparison
- Do NOT write raw data or timestamps — only patterns
