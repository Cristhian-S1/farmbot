# Repository Guidelines

## Project Structure & Module Organization

This repository documents **Sabueso**, a Proyecto IV system for monitoring tomato crops. Two teams share it: a ground team (Unitree Go2 robot) and an aerial team.

- `documentacion/`: project context only. `planeacion/` holds course instructions and semester planning; `fases/` holds requirements, stage reports and assessment rubrics (see `fase1_informe_etapa_1.md` for the current stage scope); `fases/diagramas/` holds standalone HTML diagrams with SVG assets in `svg/`.
- `terrestre/`: ground robot software (our team). Currently empty.
- `aereo/`: aerial system (the other team). Currently empty.
- `interfaz/`: user interface shared by both systems. Currently empty.
- `.beads/`: issue-tracking data; `.agents/skills/beads/`: local workflow instructions.

## Build, Test, and Development Commands

CI (`.github/workflows/ci.yml`) only checks whitespace for now; each team adds its own build and test jobs when its folder gets code.

- `python3 -m http.server 8000 --bind 127.0.0.1`: optional preview server from the repository root. Open `http://127.0.0.1:8000/documentacion/fases/diagramas/contexto.html` to review a diagram.
- `git diff --check`: check unstaged changes for whitespace errors.
- `bd prime`: load the repository's Beads workflow guidance.

## Coding Style & Naming Conventions

Write project reports and diagram labels in Spanish, preserving accents and established terminology. Use Markdown headings, concise paragraphs, relative asset links, and descriptive image alt text. Preserve existing section numbering and requirement identifiers.

Follow surrounding HTML/CSS indentation, generally two spaces. Reuse existing colors, typography, and accessible SVG titles/descriptions. Use descriptive lowercase underscore filenames for new diagrams, such as `casos_uso.html`. Keep corresponding HTML and SVG diagrams consistent.

## Testing Guidelines

Validation of documentation is manual. Preview changed Markdown and HTML, verify links and image paths, and inspect SVG labels for clipping or overlap. Check report content against `documentacion/fases/rubrica_de_etapas_informes.md`. Treat proposed software acceptance metrics as requirements, not executed tests.

## Commit & Pull Request Guidelines

Recommended messages are short and imperative, for example `docs: clarify stage 1 requirements`. Keep changes focused and within one team's folder when possible. PR descriptions should state the purpose, affected folders, validation performed, and related Beads issue; include screenshots for visual changes.

## Agent-Specific Instructions

When `.codegraph/` exists, use `codegraph_explore` or `codegraph explore "<question>"` before searching or reading code. If it returns no relevant results, inspect files directly. Do not create an index when absent.

Use Beads for task tracking and persistent memory; consult `.agents/skills/beads/SKILL.md`. Do not commit, push, or synchronize remote data without authorization.
