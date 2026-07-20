# federation-map

**The Agent Federation visualized. One ASCII map. Real data. No bullshit.**

<!-- federation-map:start -->

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #1 · 2026-07-20T04:54:58Z│
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high │
│  8 nodes · 5 communicating · 202 in flight · 5/8 feeds               │
├──────────────────────────────────────────────────────────────────────┤
│  INTERNET · relay/transport                                          │
│    █ agent-internet         ·····   144                              │
│────────────────────────────────────────────────────────────────────  │
│  PROTOCOL · governance/authority                                     │
│    · steward-protocol       ·····     0    feed · silent             │
│────────────────────────────────────────────────────────────────────  │
│  NODE · execution/citizens                                           │
│    █ steward                ·····    52    feed                      │
│    ░ agent-research         ·····     3    feed                      │
│    ░ hermes-sankhya-25      ·····     2    feed                      │
│    ░ agent-world            ·····     1    feed                      │
│    · agent-city             ·····     0    silent                    │
│    · steward-test           ·····     0    template                  │
│────────────────────────────────────────────────────────────────────  │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION FLOWS · directed, from live NADI envelopes               │
│    agent-internet       ──▶ steward                88  ████          │
│    agent-internet       ──▶ agent-research         41  ██            │
│    steward              ──▶ hermes-sankhya-25      15  █             │
│    steward              ──▶ agent-city             12  █             │
│    agent-internet       ──▶ agent-city             10  █             │
│    steward              ──▶ agent-internet          9  █             │
│    steward              ──▶ agent-research          8  █             │
│    steward              ──▶ steward-federation      8  █             │
│    agent-internet       ──▶ hermes-sankhya-25       5  █             │
│    agent-research       ──▶ agent-internet          3  █             │
│    hermes-sankhya-25    ──▶ agent-internet          2  █             │
│    agent-world          ──▶ agent-internet          1  █             │
│    silent: agent-city, steward-protocol, steward-test                │
├──────────────────────────────────────────────────────────────────────┤
│  FEDERATION PULSE                                                    │
│    nodes         8   ▁▁▁▁▁  steady                                   │
│    comming       5   ·····                                           │
│    in flight   202   ·····                                           │
│    feeds       5/8   ▁▁▁▁▁  steady                                   │
│    busiest     agent-internet · 144 pending                          │
│    quietest    agent-city · 0 msgs                                   │
├──────────────────────────────────────────────────────────────────────┤
│  TERRA MAP · structure = geography · activity = weather              │
│  ── RELAY                                                            │
│      ~    ~    ~    ~    ~  █ ~    ~    ~    ~    ~                  │
│     ~    ~    ~    ~    ~    ~    ~    ~    ~    ~    ~              │
│  ── GOVERN                                                           │
│    ▲    ▲    ▲    ▲    ▲    ·    ▲    ▲    ▲    ▲    ▲               │
│   ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲                │
│  ── RESEARCH                                                         │
│  ≈    ≈    ≈    ≈    ≈    ≈ ░  ≈    ≈    ≈    ≈    ≈                 │
│      ≈    ≈    ≈    ≈    ≈    ≈    ≈    ≈    ≈    ≈                  │
│  ── EXEC                                                             │
│     ▓    ▓    ▓    ▓    ▓   █▓    ▓    ▓    ▓    ▓    ▓              │
│    ▓    ▓    ▓    ▓    ▓    ▓    ▓    ▓    ▓    ▓    ▓               │
│  ── OUTPOST                                                          │
│   ·    ·   ░·    ·    ·    ·░   ·    ·    · ·  ·    ·                │
│  ·    ·    ·    ·    ·    ·    ·    ·    ·    ·    ·                 │
│  ── SANDBOX                                                          │
│      ◇    ◇    ◇    ◇    ◇  · ◇    ◇    ◇    ◇    ◇                  │
│     ◇    ◇    ◇    ◇    ◇    ◇    ◇    ◇    ◇    ◇    ◇              │
│                                                                      │
│  █  1 agent-internet    ·  2 agent-city    ░  3 agent-research       │
│  █  4 steward    ░  5 agent-world    ░  6 hermes-sankhya-…           │
│  ·  7 steward-protocol    ·  8 steward-test                          │
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
