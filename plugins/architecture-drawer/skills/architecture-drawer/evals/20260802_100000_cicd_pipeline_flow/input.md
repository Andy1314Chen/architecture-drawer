# CI/CD Deployment Pipeline — Flowchart

A top-to-bottom **process flowchart** (not an architecture diagram). Color
encodes the standard flowchart role vocabulary: green = start/end terminator,
blue = process, yellow = decision, orange = I/O, purple = subprocess.

## Flow

1. **Start** (green terminator) — a commit is pushed.
2. **Webhook** (orange hexagon, I/O input) — push event arrives.
3. **Build** (blue process).
4. **Build OK?** (yellow decision):
   - **No** → **Notify Failure** (blue process, left branch) → **Failed** (green
     terminator, left column).
   - **Yes** → continue down the spine.
5. **Test Suite** (purple subprocess, **double border**) — runs unit +
   integration tests.
6. **Tests Pass?** (yellow decision):
   - **No** → straight left into the same **Failed** terminator (convergence).
   - **Yes** → continue down the spine.
7. **Deploy to Prod** (blue process).
8. **Released** (green terminator) — happy path end.

Two decisions branch **No** to the left and converge on a single **Failed**
end node; the **Yes** paths stay on the vertical center spine.

## Design

- Palette: the **flowchart role palette** (green/blue/yellow/orange/purple hue
  pairs) — a self-contained, justified >8-accent scheme (color = role).
- Font tiers: 20 / 14 / 12 / 10 (title / node label / sub-label / branch flag).
- Both branches of every decision are labelled ("是 Yes" / "否 No").
- Canvas ~1000 × 1240. Edges gray (`#4D4D4D`); TB spine, left detour for the
  failure convergence.
