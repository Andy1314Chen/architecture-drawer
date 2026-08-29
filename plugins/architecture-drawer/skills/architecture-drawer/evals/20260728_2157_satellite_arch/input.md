# Integrated Space-Ground Satellite System Architecture

天地一体化卫星系统架构分层图 (Integrated Space-Ground Satellite Architecture) — a layered
diagram mapping satellite subsystems across orbital-altitude bands (bottom = ground,
top = deep space), with a horizontal functional color code distinguishing what each
satellite does (comm / nav / sensing / manned).

## Layers (bottom → top)

1. **Ground Segment (地面支撑层)** — ground stations, TT&C, mission control,
   data receiving antennas, satellite control center. White-filled nodes.
2. **LEO Constellation (低地球轨道, the densest layer)** — three sub-rows:
   a mesh of low-orbit comm satellites (starlink/千帆 style) with
   inter-satellite links; a row of sensing satellites
   (optical/radar/resource) and a remote-sensing data source; a small
   science-probe sub-row; plus the manned 天宫 space station.
3. **MEO Navigation (中地球轨道)** — navigation constellation (北斗/GPS/Galileo)
   arranged as a staggered two-row ring with downward coverage beams.
4. **GEO / IGSO (地球静止轨道)** — geostationary relay, broadcast, weather,
   and strategic-warning satellites riding a single dashed orbital arc.
5. **Deep Space (深空探测 / 拉格朗日点)** — space telescopes and probes near
   the L1/L2 Lagrange points, plus a note on highly-elliptical (闪电) orbits.

The ground segment closes the diagram at the bottom with an earth-horizon
curve and a ground-segment caption beneath it.

## Functional color code (horizontal)

- **Blue** = communication payloads and data-relay links (incl. 天链 relay)
- **Green** = navigation / positioning (北斗, GPS, Galileo)
- **Orange** = sensing / earth observation / research probes
- **Slate** = manned platforms / stations / structural (天宫, ground stations)

Each layer contains nodes colored by their function.

## Flow & edges

- **LEO comm mesh**: link-style connectors between consecutive comm
  satellites (a mesh, not a flow — no arrowheads).
- **Validated relay chain (the concrete data path, draw these as real
  edges):** remote-sensing source → GEO relay → ground control (sensing data
  flowing up, then down).
- **LEO↔MEO inter-satellite link:** a dashed cross-layer constellation link,
  no arrowhead.
- Decorative uplink/downlink arrow pairs (solid up, dashed down) may sit
  beside ground stations — mark them decorative, not real edges.

Node shapes distinguish subsystem kinds (circles for satellites, squares for
ground/station nodes, apex-up triangles for probes/telescopes, diamonds for
Lagrange markers). Layout, exact palette, typography, and all geometry are
yours to design — follow the architecture-drawer skill's design system and
let the evaluator guide iteration.
