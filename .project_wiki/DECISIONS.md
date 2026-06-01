# Codex SpecPilot — DECISIONS

## D001 — No LLM in v1

**Date**: 2026-05-31  
**Decision**: Hook implementations use only Python standard library rules.  
**Rationale**: Keep the first release minimal and testable.  
**Status**: Accepted

## D002 — Default verdict is human_review

**Date**: 2026-05-31  
**Decision**: StopJudge always returns `human_review` in v1.  
**Rationale**: Prevent auto-loop from breaking anything before hooks are stable.  
**Status**: Accepted

## D003 — No Subagent, PostToolUse, PreCompact, run_task.py

**Date**: 2026-05-31  
**Decision**: These hooks and the scheduler are out of scope for v1.  
**Rationale**: Focus on the three core hooks first.  
**Status**: Accepted
