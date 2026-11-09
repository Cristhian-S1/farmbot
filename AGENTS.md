# Repository Guidelines

## Project Structure & Module Organization

This repository documents **Sabueso**, a Proyecto IV system for monitoring tomato crops. It is maintained by a single team (Unitree Go2 ground robot).

- `documentacion/`: project context. `planeacion/` holds course instructions and semester planning; `fases/` holds requirements, stage reports and assessment rubrics (see `fase1_informe_1.md` for the current stage scope); `fases/diagramas/` holds standalone HTML diagrams with SVG assets in `svg/`; `guias/` holds operator guides (VirtualBox, network and OVA export).
- `src/`: robot software (camera, detection, route, registration and live streaming).
- `ui/`: user interface: Flask API in `ui/api/` and React/Vite web in `ui/web/`.
- `scripts/red/`: VM/PC ↔ robot network setup (static IP, NAT, dock internet and verification).
- `.beads/`: issue-tracking data; `.agents/skills/beads/`: local workflow instructions.

## Build, Test, and Development Commands

CI (`.github/workflows/ci.yml`) checks whitespace, runs `shellcheck` on `scripts/red/*.sh` and compiles `src/` and `ui/api/`.

- `shellcheck scripts/red/*.sh`: lint the network scripts.
- `python3 -m compileall -q src ui/api`: check Python syntax without hardware.
- `cd ui/web && npm ci && npm run build`: build the web interface (Node 20 or newer).
- `python3 -m http.server 8000 --bind 127.0.0.1`: optional preview server from the repository root. Open `http://127.0.0.1:8000/documentacion/fases/diagramas/contexto.html` to review a diagram.
- `git diff --check`: check unstaged changes for whitespace errors.
- `bd prime`: load the repository's Beads workflow guidance.

## Coding Style & Naming Conventions

Write project reports and diagram labels in Spanish, preserving accents and established terminology. Use Markdown headings, concise paragraphs, relative asset links, and descriptive image alt text. Preserve existing section numbering and requirement identifiers.

Follow surrounding HTML/CSS indentation, generally two spaces. Reuse existing colors, typography, and accessible SVG titles/descriptions. Use descriptive lowercase underscore filenames for new diagrams, such as `casos_uso.html`. Keep corresponding HTML and SVG diagrams consistent.

## Testing Guidelines

Validation of documentation is manual. Preview changed Markdown and HTML, verify links and image paths, and inspect SVG labels for clipping or overlap. Check report content against `documentacion/fases/rubrica_de_etapas_informes.md`. The network scripts are checked with `shellcheck`; `src/` and `ui/api/` are compiled in CI, but there are still no automated tests for the web or the robot software. Treat proposed software acceptance metrics as requirements, not executed tests.

## Commit & Pull Request Guidelines

Recommended messages are short and imperative, for example `docs: clarify stage 1 requirements`. Keep changes focused and within one folder when possible. PR descriptions should state the purpose, affected folders, validation performed, and related Beads issue; include screenshots for visual changes.

## Agent-Specific Instructions

When `.codegraph/` exists, use `codegraph_explore` or `codegraph explore "<question>"` before searching or reading code. If it returns no relevant results, inspect files directly. Do not create an index when absent.

For a code graph that also covers the shell scripts, use `graphify query "<question>"` over `graphify-out/` (built with `graphify extract . --code-only`); rebuild it with `graphify update .` after code changes. Both indexes are local and ignored by Git.

Use Beads for task tracking and persistent memory; consult `.agents/skills/beads/SKILL.md`. Do not commit, push, or synchronize remote data without authorization.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
