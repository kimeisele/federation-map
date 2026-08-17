# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #515 · 2026-08-17T14:49:51Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  5 nodes · 0 communicating · 0 in flight · 0/5 feeds                 │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    ─ agent-internet         ████▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    ─ agent-world            ▁▁▁▁▁     —    unreachable               │
│    ─ steward-protocol       ▁▁▁▁▁     —    unreachable               │
│    ─ steward                ▆▆▅▁▁     —    unreachable               │
│    ─ steward-test           ████▁     —    unreachable               │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  (no flow data — envelopes may lack target_city_id)                  │

├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         5   ▁▁▁▁▁  steady                                   │
│    comming       0   ███▆▁  ↓                                        │
│    in flight     0   ▇▇▇▅▁  ↓  -145                                  │
│    feeds       0/5   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 0 pending                            │
│    quietest    agent-internet · 0 msgs                               │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│                                                                      │
│                             ─                                        │
│                                                                      │
│  ── EXEC                                                             │
│                                                                      │
│                             ─                                        │
│                                                                      │
│  ── SANDBOX                                                          │
│                                                                      │
│                             ─                                        │
│                                                                      │
│  ── OPEN                                                             │
│                                                      ─               │
│    ─                                                                 │
│                                                                      │
│  ─  1 agent-internet !    ─  2 steward !    ─  3 steward-test !      │
│  ─  4 agent-world !    ─  5 steward-protocol !                       │
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
