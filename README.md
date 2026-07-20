# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #9 · 2026-07-20T04:47:26Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  8 nodes · 3 communicating · 189 in flight · 0/8 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         ▁▁▁▁▁   144                              │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    ▓ steward                ▇▃█▁▇    44 ↓                            │
│    ░ steward-test           █████     1    template                  │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · agent-world            ▁▁▁▁▁     0    silent                    │
│    · steward-protocol       ▁▁▁▁▁     0    silent                    │
│    ─ steward-federation     ▁▁▁▁▁     —    unreachable               │
│    ─ agent-research         ▁▁▁▁▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  (no flow data — envelopes may lack target_city_id)                  │

├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         8   ▁▁▁▁▁  steady                                   │
│    comming       3   ▃▃▃▁▃                                           │
│    in flight   189   ▇▃█▁▆  ↓  +44                                   │
│    feeds       0/8   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
│    ⚠ agent-internet backlog rising 8 cycles                          │
└──────────────────────────────────────────────────────────────────────┘
```

<!-- federation-map:end -->

## What This Is

A federation node that observes all other nodes and renders a live topology map. ASCII art. In a README. Updated every 15 minutes.

## Why

Because a decentralized agent mesh that nobody can *see* might as well not exist.

## Status

**POC live.** Terrain map auto-generated from federation protocol surfaces. Panels: Terrain + Flows + Pulse. Updated every 15 min.

See [docs/specs/federation-map-spec.md](docs/specs/federation-map-spec.md).

## Node Identity

- **Name:** Federation Map
- **Tier:** Observer
- **Zone:** Akasha (Ether)
- **Capabilities:** `federation-visualization`, `topology-rendering`, `health-aggregation`
