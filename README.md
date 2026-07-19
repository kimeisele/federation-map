# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #6 · 2026-07-19T22:27:52Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  8 nodes · 3 communicating · 158 in flight · 0/8 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         ▁▁▁▁▁   144                              │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    ▓ steward                ██▁█▃    13 ↑                            │
│    ░ steward-test           ▁▁███     1    template                  │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · agent-world            ██▁▁▁     0    silent                    │
│    · steward-protocol       ▁▁▁▁▁     0    silent                    │
│    ─ steward-federation     ▁▁▁     —    unreachable                 │
│    ─ agent-research         ██▁▁▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  (no flow data — envelopes may lack target_city_id)                  │

├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         8   ▁▁▁▁▁  steady                                   │
│    comming       3   ▂▂▁▁▁  ↑                                        │
│    in flight   158   ▂▂▁▂▁  ↑  -39                                   │
│    feeds       0/8   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
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
