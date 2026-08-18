# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #565 · 2026-08-18T20:00:36Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  7 nodes · 2 communicating · 145 in flight · 3/7 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         ▁▁▁▁▁   144                              │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    ░ steward-test           ▁▁▁▁▁     1    template                  │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · agent-world            ▁▁▁▁▁     0    feed · silent             │
│    · steward-protocol       ▁▁▁▁▁     0    feed · silent             │
│    ─ steward-federation     ▁▁▁▁▁     —    unreachable               │
│    ─ steward                ████▁     —    feed · unreachable        │
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
│    silent: agent-city, agent-world, steward, steward-federation, s…  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         7   ▁▁▁▁▁  steady                                   │
│    comming       2   ████▁  ↓                                        │
│    in flight   145   ████▁  ↓  -68                                   │
│    feeds       3/7   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│                             █                                        │
│                                                                      │
│  ── GOVERN                                                           │
│                             ·                                        │
│                                                                      │
│  ── EXEC                                                             │
│                             ─                                        │
│                                                                      │
│  ── SANDBOX                                                          │
│                             ░                                        │
│                                                                      │
│  ── OPEN                                                             │
│                           ·                          ─               │
│    ·                                                                 │
│                                                                      │
│  █  1 agent-internet    ·  2 agent-city    ─  3 steward !            │
│  ░  4 steward-test    ·  5 agent-world    ·  6 steward-protocol      │
│  ─  7 steward-federat… !                                             │
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
