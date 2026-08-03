# CI/CD 部署流水线 — Deployment Pipeline Flowchart

A top-to-bottom **process flowchart** for a realistic CI/CD pipeline with four
quality-gate decisions. Color encodes the standard flowchart role vocabulary:
green = start/end terminator, blue = process, yellow = decision, orange = I/O,
purple = subprocess (double border). Gray junction circles mark merge points
where multiple failure branches converge.

## Pipeline stages & flow

### Trigger
1. **Start** (green terminator) — a commit is pushed to `main` or a PR merged.
2. **Webhook** (orange hexagon, I/O input) — push event received.

### Build
3. **Checkout & Build** (purple subprocess) — `git clone`, dependency install
   (`npm ci`), compile / bundle the artifact.
4. **Build OK?** (yellow decision):
   - **No** → enters the failure column (left).
   - **Yes** → continues down the spine.

### Quality gates
5. **Lint & Security Scan** (purple subprocess) — ESLint, MyPy type check, SAST
   vulnerability scan.
6. **Lint OK?** (yellow decision):
   - **No** → failure column.
   - **Yes** → continues.
7. **Test Suite** (purple subprocess) — unit, integration, and end-to-end tests.
8. **Tests Pass?** (yellow decision):
   - **No** → failure column.
   - **Yes** → continues.

### Staging & production
9. **Deploy to Staging** (blue process) — `kubectl apply`, rolling update on the
   staging cluster.
10. **Smoke Tests** (blue process) — health probes, API contract checks.
11. **Smoke OK?** (yellow decision):
    - **No** → failure column.
    - **Yes** → continues.
12. **Deploy to Prod** (blue process) — canary (10 % traffic) → blue-green
    promotion.
13. **Released** (green terminator) — happy-path end.

### Failure convergence (left column)
All four decisions branch **No** to the left. The first failure route hits
**Notify Failure** (blue process — Slack / Email alert); subsequent failure
routes merge via gray junction circles and all converge on a single **Failed**
green terminator. The **Yes** paths stay on the vertical center spine.

## Design

- **Palette**: the flowchart role palette (green / blue / yellow / orange /
  purple hue pairs) — a self-contained, justified >8-accent scheme (color =
  role). Junctions use neutral gray (not counted as accents).
- **Font tiers**: 20 / 14 / 12 / 10 (title / node label / subtitle / sub-label
  & branch flag).
- **Bilingual labels**: every node carries a Chinese main label and an English
  or tool-name sub-label. Terminator labels are Chinese-only (开始 / 已发布 /
  失败), placed outside their circles.
- Both branches of every decision are labelled ("是 Yes" / "否 No").
- **Canvas** ~1000 × 1720. Edges gray (`#4D4D4D`); TB spine, left failure
  column with junction merge points.
