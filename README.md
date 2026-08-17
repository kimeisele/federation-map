# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #518 · 2026-08-17T15:53:49Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  5 nodes · 1 communicating · 144 in flight · 2/5 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         █▁███   144                              │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · agent-world            ▁▁▁▁▁     0    feed · silent             │
│    · steward-protocol       ▁▁▁▁▁     0    feed · silent             │
│    ─ steward-federation     ▁▁▁▁▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION FLOWS · directed, from live NADI envelopes               │
│    agent-internet       ──▶ steward                34  ████          │
│    agent-internet       ──▶ agent-research         19  ██            │
│    agent-internet       ──▶ steward-test           19  ██            │
│    agent-internet       ──▶ agent-city             18  ██            │
│    agent-internet       ──▶ agent-world            18  ██            │
│    agent-internet       ──▶ steward-protocol       18  ██            │
│    agent-internet       ──▶ steward-federation     18  ██            │
│    silent: agent-city, agent-world, steward-federation, steward-pr…  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         5   ▁▁▁▁▁  steady                                   │
│    comming       1   ▆▁▆▃▃  ↓                                        │
│    in flight   144   ▆▁▆▆▆  ↓  +0                                    │
│    feeds       2/5   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│                                                                      │
│                             █                                        │
│                                                                      │
│                                                                      │
│  ── GOVERN                                                           │
│                                                                      │
│                             ·                                        │
│                                                                      │
│                                                                      │
│  ── OPEN                                                             │
│                           ·                                          │
│                                                      ─               │
│    ·                                                                 │
│                                                                      │
│                                                                      │
│  █  1 agent-internet    ·  2 agent-city    ·  3 agent-world          │
│  ·  4 steward-protocol    ─  5 steward-federat… !                    │
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
