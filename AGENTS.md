# Repository Guidelines

## Project Structure & Module Organization

This repository documents **Sabueso**, a Proyecto IV system for monitoring tomato crops with a Unitree Go2 robot. It currently contains documentation and static diagrams, rather than an implemented application.

- `planeacion/`: course instructions and semester planning.
- `fases/`: requirements, stage reports, and assessment rubrics. Consult `fase1_informe_etapa_1.md` for the current stage scope.
- `fases/diagramas/`: standalone HTML diagrams; `svg/` contains diagram assets embedded in reports.
- `.beads/`: issue-tracking data; `.agents/skills/beads/`: local workflow instructions.

- `robot/sabueso_robot/`: software for the robot dock; `seguridad/` is the only module allowed to command motion.
- `scripts/red/`, `scripts/robot/`: network setup (PC or VirtualBox VM ↔ robot) and read-only robot inventory.
- `config/`: network, CycloneDDS and safety-limit templates (never store secrets).
- `docs/`: operator guides; `tests/`: hardware-free `pytest` suites.

## Build, Test, and Development Commands

`pyproject.toml` configures `pytest`; CI (`.github/workflows/ci.yml`) runs `pytest` and `shellcheck`.

- `python3 -m pytest`: run hardware-free tests.
- `shellcheck scripts/red/*.sh scripts/robot/*.sh`: lint shell scripts.

- `python3 -m http.server 8000 --bind 127.0.0.1`: optional preview server from the repository root. Open `http://127.0.0.1:8000/fases/diagramas/contexto.html` to review a diagram.
- `git diff --check`: check unstaged changes for whitespace errors.
- `git diff -- AGENTS.md fases/ planeacion/`: review documentation changes before staging.
- `bd prime`: load the repository's Beads workflow guidance.

## Coding Style & Naming Conventions

Write project reports and diagram labels in Spanish, preserving accents and established terminology. Use Markdown headings, concise paragraphs, relative asset links, and descriptive image alt text. Preserve existing section numbering and requirement identifiers.

Follow surrounding HTML/CSS indentation, generally two spaces. Reuse existing colors, typography, and accessible SVG titles/descriptions. Use descriptive lowercase underscore filenames for new diagrams, such as `casos_uso.html`. Keep corresponding HTML and SVG diagrams consistent. No formatter or linter is configured.

## Testing Guidelines

Validation is currently manual; there is no testing framework or coverage threshold. Preview changed Markdown and HTML, verify links and image paths, and inspect SVG labels for clipping or overlap. Check report content against `fases/rubrica_de_etapas_informes.md`. Treat proposed software acceptance metrics as requirements, not executed tests.

## Commit & Pull Request Guidelines

Recommended messages are short and imperative, for example `docs: clarify stage 1 requirements`. Keep changes focused. PR descriptions should state the purpose, affected reports, validation performed, and related Beads issue; include screenshots for visual changes.

## Agent-Specific Instructions

When `.codegraph/` exists, use `codegraph_explore` or `codegraph explore "<question>"` before searching or reading code. If it returns no relevant results, inspect files directly. Do not create an index when absent.

Use Beads for task tracking and persistent memory; consult `.agents/skills/beads/SKILL.md`. Do not commit, push, or synchronize remote data without authorization.
