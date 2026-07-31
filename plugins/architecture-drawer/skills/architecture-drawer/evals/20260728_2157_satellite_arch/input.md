# Integrated Space-Ground Satellite System Architecture

天地一体化卫星系统架构分层图 — an integrated space-ground satellite architecture.

Bottom = ground, top = deep space. Five vertical layers, with a horizontal
functional color code distinguishing satellite subsystems.

## Layers (bottom → top)

1. **Ground Segment** — ground stations, TT&C, mission control, data processing.
2. **Link Layer** — communication links, uplink/downlink, relay.
3. **LEO Constellation** — low-earth-orbit satellites (communication, navigation,
   earth observation).
4. **GEO / MEO** — geostationary / medium-orbit relay and broadcast satellites.
5. **Deep Space** — inter-satellite links, deep-space probes.

## Functional color code (horizontal)

- **Blue** = communication payloads
- **Green** = navigation / positioning
- **Orange** = sensing / earth observation / research

Each layer contains nodes colored by their function; bidirectional arrows show
sensing (up) and control (down) flows between layers.

## Design

- Background light. Arrowheads neutral black (no dark/light clash in either channel).
- Arrowheads use a single shared marker definition.
- Font tiers: 4 tiers.
