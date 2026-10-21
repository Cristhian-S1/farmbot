# Repository Guidelines

## Project Structure & Module Organization

This repository documents **Sabueso**, a Proyecto IV system for monitoring tomato crops with a Unitree Go2 robot. It currently contains documentation and static diagrams, rather than an implemented application.

- `planeacion/`: course instructions and semester planning.
- `fases/`: requirements, stage reports, and assessment rubrics. Consult `fase1_informe_etapa_1.md` for the current stage scope.
- `fases/diagramas/`: standalone HTML diagrams; `svg/` contains diagram assets embedded in reports.
- `.beads/`: issue-tracking data; `.agents/skills/beads/`: local workflow instructions.

There are no application source or test directories yet.

## Build, Test, and Development Commands

No build system, package manifest, or automated test runner is configured.

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

The repository has no commits yet, so no historical convention exists. Recommended messages are short and imperative, for example `docs: clarify stage 1 requirements`. Keep changes focused. PR descriptions should state the purpose, affected reports, validation performed, and related Beads issue; include screenshots for visual changes.

## Agent-Specific Instructions

When `.codegraph/` exists, use `codegraph_explore` or `codegraph explore "<question>"` before searching or reading code. If it returns no relevant results, inspect files directly. Do not create an index when absent.

Use Beads for task tracking and persistent memory; consult `.agents/skills/beads/SKILL.md`. Do not commit, push, or synchronize remote data without authorization.
