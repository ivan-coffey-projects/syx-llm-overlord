---
tags:
  - syx
  - wiki
  - moc
---

# Syx LLM Overlord Wiki

Knowledge base for the AI overlord: how it plays, what it remembers, and how the stack fits together.

## Rules & playbooks

- [Starter Playbook](rules/playbook.md) — **source of truth** injected into every LLM tick
- [Teacher mode](modes/teacher.md) — teaches player while playing
- [Civil Flow State](modes/civil-flow.md) — wiki-backed expert autopilot
- [Command API](rules/commands.md) — what actions work vs stubs
- [Room types & aliases](rules/rooms.md) — build targets the mod understands
- [Failure messages](rules/failures.md) — how to read and recover from errors

## Memory system

- [Live session log](memory/live-log.md) — **auto-updated** mirror of JSONL (bridge writes each tick)
- [Memory overview](memory/overview.md) — session log + prompt injection
- [JSONL log format](memory/log-format.md) — file structure and entry kinds
- [Operations](memory/operations.md) — API, dashboard, manual notes

## Architecture

- [Stack diagram](architecture/stack.md) — mod → bridge → LLM → dashboard
- [Paths & ports](architecture/paths.md) — where everything lives on disk

## Research

- [Prior art](research/prior-art.md) — has anyone done this before?

## Project

- [Project hub](../project.md) — status, links, launcher

## Editing rules

When you edit [rules/playbook](rules/playbook.md), changes apply on the **next tick** automatically (bridge reads the file each decision). Optional: `POST http://localhost:3847/api/playbook/reload` to verify load.

Memory is **runtime** (JSONL at `logs/overlord-memory.jsonl`). The bridge mirrors the tail into [memory/live-log](memory/live-log.md) each tick. Copy durable lessons into [rules/playbook](rules/playbook.md) or add manual notes via dashboard / `POST /api/memory`.
