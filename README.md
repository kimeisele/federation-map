# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #54 · 2026-07-24T09:36:35Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  7 nodes · 3 communicating · 209 in flight · 2/7 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         ▁▁▁▁▁   144                              │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    █ steward                █▅█▁▁    64 ↓  feed                      │
│    ░ steward-test           ▁▁▁▁▁     1    template                  │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · steward-protocol       ▁▁▁▁▁     0    feed · silent             │
│    ─ steward-federation     ▁▁▁▁▁     —    unreachable               │
│    ─ agent-research         ▁▁▁▁▁     —    unreachable               │
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
│    steward              ──▶ agent-city              4  █             │
│    steward              ──▶ agent-world             4  █             │
│    steward              ──▶ steward                 4  █             │
│    steward              ──▶ steward-protocol        4  █             │
│    steward              ──▶ steward-federation      4  █             │
│    silent: agent-city, agent-research, steward-federation, steward…  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         7   ▁▁▁▁▁  steady                                   │
│    comming       3   ▁▁▁▁▁                                           │
│    in flight   209   █▅█▁▁  ↓  +0                                    │
│    feeds       2/7   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
│    ⚠ agent-internet backlog rising 54 cycles                         │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│                             █                                        │
│  ── GOVERN                                                           │
│                             ·                                        │
│  ── RESEARCH                                                         │
│                             ─                                        │
│  ── EXEC                                                             │
│                             █                                        │
│  ── SANDBOX                                                          │
│                             ░                                        │
│  ── OPEN                                                             │
│    ─                                                 ·               │
│                                                                      │
│  █  1 agent-internet    ·  2 agent-city    ─  3 agent-research !     │
│  █  4 steward    ░  5 steward-test    ─  6 steward-federat… !        │
│  ·  7 steward-protocol                                               │
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
