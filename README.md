# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #203 · 2026-08-05T22:44:43Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  8 nodes · 1 communicating · 64 in flight · 3/8 feeds                │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    ─ agent-internet         ████▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    █ steward                ██▁▇▇    64 ↑  feed                      │
│    · agent-city             ▁▁▁▁▁     0    silent                    │
│    · agent-world            ▁▁▁▁▁     0    feed · silent             │
│    · steward-protocol       ▁▁▁▁▁     0    feed · silent             │
│    ─ steward-federation     ▁▁▁▁▁     —    unreachable               │
│    ─ agent-research         ▁▁▁▁▁     —    unreachable               │
│    ─ steward-test           ████▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION FLOWS · directed, from live NADI envelopes               │
│    steward              ──▶ agent-city              4  ████          │
│    steward              ──▶ agent-world             4  ████          │
│    steward              ──▶ steward                 4  ████          │
│    steward              ──▶ steward-protocol        4  ████          │
│    steward              ──▶ steward-federation      4  ████          │
│    steward              ──▶ steward-gateway         4  ████          │
│    steward              ──▶ agent-internet          4  ████          │
│    steward              ──▶ agent-template          4  ████          │
│    steward              ──▶ agent-research          4  ████          │
│    steward              ──▶ steward-test            4  ████          │
│    steward              ──▶ hermes-sankhya-25       4  ████          │
│    steward              ──▶ agent-village           4  ████          │
│    silent: agent-city, agent-internet, agent-research, agent-world…  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         8   ▁▁▁▁▁  steady                                   │
│    comming       1   ████▁  ↓                                        │
│    in flight    64   ██▆█▁  ↓  -145                                  │
│    feeds       3/8   ▁▁▁▁▁  steady                                   │
│    busiest     steward · 64 pending                                  │
│    quietest    agent-internet · 0 msgs                               │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│                             ─                                        │
│  ── GOVERN                                                           │
│                             ·                                        │
│  ── RESEARCH                                                         │
│                             ─                                        │
│  ── EXEC                                                             │
│                             █                                        │
│  ── SANDBOX                                                          │
│                             ─                                        │
│  ── OPEN                                                             │
│    ·                      ·                          ─               │
│                                                                      │
│  ─  1 agent-internet !    ·  2 agent-city    ─  3 agent-research !   │
│  █  4 steward    ─  5 steward-test !    ·  6 agent-world             │
│  ·  7 steward-protocol    ─  8 steward-federat… !                    │
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
