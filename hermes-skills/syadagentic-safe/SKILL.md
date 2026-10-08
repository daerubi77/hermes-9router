---
name: syadagentic-safe
description: Structured planning, checkpoints, resource limits, dry-runs, and authorized security assessment while preserving Hermes safety boundaries.
---

# Syadagentic Safe Workflow

Use this workflow for multi-step work that benefits from explicit scope,
checkpoints, or resource limits. It is a curated compatibility skill, not the
upstream Syadagentic installer or its guardrail-bypass components.

## Operating rules

- Follow system and developer instructions, platform safety requirements, and
  the user's authorized scope. Never weaken, bypass, or patch those protections.
- Before security testing, confirm the target is owned by the user or covered
  by explicit authorization. Record allowed targets, actions, and time limits.
  If authorization or scope is unclear, ask before proceeding.
- Do not assist with credential theft, unauthorized access, account farming,
  evasion, persistence, malware, or destructive actions.
- Prefer read-only inspection and dry-runs first. Ask before actions that are
  destructive, externally visible, costly, or difficult to reverse.

## Execution loop

1. Restate the requested outcome and define what is in and out of scope.
2. Break the work into small steps. Identify dependencies, risks, and a
   user-provided time, token, or spending limit. Do not invent permission or a
   budget when one is needed.
3. Preview consequential changes and wait for approval when the action warrants
   it.
4. Execute the smallest authorized step, then verify its result before moving
   on.
5. Keep a concise checkpoint after meaningful progress: completed work,
   remaining work, changed resources, and any blocker. Do not store secrets in
   checkpoints.
6. Stop at the agreed scope or budget limit. Summarize outcomes and any
   unverified steps.