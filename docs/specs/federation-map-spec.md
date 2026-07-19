# Federation Map — Specification v0.2

**Status:** Draft — POC
**Goal:** A single-file, auto-generated, ASCII-art topology map of the live Agent Federation. Driven by federation protocols, not URL scraping. Every data point comes from `.well-known/`, NADI, or the authority feed.

> **Principle:** Read-only on the federation. This node observes via the same protocols every other node uses. No shortcuts through internal files. No assumptions about what another node stores where.

---

## NORTH STAR

**Make the invisible federation visible — through its own protocols.** A developer, agent, or curious outsider opens one README and sees what the federation *declares about itself* through its standardized surfaces.

---

## What This Is NOT

- ❌ A scraper that reads arbitrary files from other repos
- ❌ A replacement for steward's Reaper or Health-Observer
- ❌ A web app, dashboard, or hosted service
- ❌ A modification to any existing federation node

## What This IS

- ✅ A federation node (built from agent-template)
- ✅ A passive observer that reads federation-standard surfaces only
- ✅ One ASCII-art map rendered into README.md
- ✅ Structured data files (`topology.json`, `peers.json`) for agent consumption
- ✅ A GitHub Actions heartbeat on the federation's own rhythm
- ✅ A public face for the federation — the thing you send someone to say "look, it's alive"

---

## Federation Protocols (the only data paths we use)

Every federation node exposes these standardized surfaces. These are the contract. Nothing else.

### Layer 1: Discovery & Identity (every node MUST have these)

| Surface | Path | What It Declares |
|---------|------|-----------------|
| Federation Descriptor | `.well-known/agent-federation.json` | `kind`, `status` (active/sleeping), `repo_id`, `layer`, `capabilities`, `endpoints` |
| NADI Peer Identity | `data/federation/peer.json` | `identity.city_id`, `identity.repo`, `endpoint.transport`, `capabilities`, `nadi.outbox`/`inbox` paths |

**Verification (2026-07-19):** 8/8 seed nodes expose the descriptor. 8/8 expose peer.json. These are the foundation.

### Layer 2: Communication Activity (NADI transport)

| Surface | Path | What It Shows |
|---------|------|--------------|
| NADI Outbox | `data/federation/nadi_outbox.json` | Pending `DeliveryEnvelope` messages. Count = communication activity. |
| NADI Inbox | `data/federation/nadi_inbox.json` | Received messages from peers. |

**Verification:** agent-internet has 144 pending outbox messages right now. steward has 52. agent-city has 0. This IS the federation's pulse — no health.json needed.

### Layer 3: Verified Content (Authority Feed)

| Surface | Path | What It Shows |
|---------|------|--------------|
| Authority Manifest | `authority-feed/latest-authority-manifest.json` | `kind` = `source_authority_feed_manifest`. Node publishes verifiable content. |

**Verification:** 4/8 nodes publish an authority feed (agent-world, steward-protocol, agent-research, steward).

### Layer 4: Peer Discovery (Federation-standard bootstrap)

| Surface | Source | What It Shows |
|---------|--------|--------------|
| Seed List | `data/federation/authority-descriptor-seeds.json` | Bootstrap peers (currently 8) |
| GitHub Topic Search | `agent-federation-node` topic | Dynamic discovery of new nodes |

**This is the same mechanism `discover_federation_peers.py` uses.** federation-map reuses this pattern, not invents a new one.

### What we deliberately do NOT read

- `CLAUDE.md` — internal agent instructions, not a federation surface
- `steward_health.json` — steward implementation detail
- `pokedex.json` — agent-city implementation detail
- Any path not declared in `.well-known/agent-federation.json` or `peer.json`

These files contain valuable data. The proper way to get that data is for those nodes to publish it via their authority feed or respond to NADI queries. That's a protocol evolution, not a scraping shortcut.

---

## Architecture

```
federation-map/
├── .well-known/
│   ├── agent-federation.json       ← This node's federation identity
│   └── agent.json                  ← This node's agent card
├── data/
│   └── federation/
│       ├── peer.json               ← This node's NADI identity
│       ├── peers.json              ← Discovered peer registry (from seeds + topic search)
│       ├── topology.json           ← Computed topology: nodes + edges + status
│       ├── nadi_outbox.json        ← NADI outbox (send topology updates)
│       └── nadi_inbox.json         ← NADI inbox (receive heartbeats from peers)
├── scripts/
│   ├── discover_peers.py           ← Reuse federation discovery pattern (seeds + topic search)
│   └── render_topology.py          ← THE CORE: reads peers.json → fetches surfaces → renders ASCII
├── docs/
│   └── specs/
│       └── federation-map-spec.md  ← This file
├── README.md                       ← Contains the live ASCII map (auto-committed by heartbeat)
└── .github/
    └── workflows/
        └── federation-map.yml      ← Heartbeat: render → commit → push
```

---

## The Core Script: `scripts/render_topology.py`

Python 3.11. Stdlib only (`urllib`, `json`, `hashlib`). Zero dependencies — same contract as every federation script.

### Phase 1: Discover Peers

```
Input:  data/federation/authority-descriptor-seeds.json (local copy, synced from hermes-sankhya-25)
        Optional: GitHub topic search "agent-federation-node"

Process:
  1. Read seed URLs
  2. Fetch .well-known/agent-federation.json from each seed
  3. Validate: kind == "agent_federation_descriptor"
  4. Extract: repo_id, status, layer, capabilities
  5. Deduplicate by repo_id
  6. Also fetch data/federation/peer.json from each (NADI identity)

Output: data/federation/peers.json
  [
    {
      "repo_id": "kimeisele/steward",
      "city_id": "steward",
      "status": "active",
      "layer": "node",
      "capabilities": ["code_analysis", "task_execution", ...],
      "nadi_outbox": "data/federation/nadi_outbox.json",
      "nadi_inbox": "data/federation/nadi_inbox.json",
      "transport": "filesystem"
    },
    ...
  ]
```

### Phase 2: Check Activity (NADI outbox)

```
For each peer with a known nadi_outbox path:
  1. Fetch {repo}/main/{nadi_outbox_path}
  2. Count pending DeliveryEnvelope messages
  3. Record: nadi_pending_count, last_message_timestamp (if available)

Node activity status derived from NADI:
  - COMMUNICATING: nadi_pending > 0 in last cycle  → node is actively sending
  - IDLE:         nadi_pending == 0                 → node is alive but quiet
  - UNREACHABLE:  outbox fetch failed               → node may be down
```

### Phase 3: Check Authority Feed

```
For each peer:
  1. Try fetching authority-feed/latest-authority-manifest.json
  2. If present and valid: node publishes verified content
  3. Record: has_authority_feed, manifest_kind
```

### Phase 4: Compute Topology

```
Nodes:  all discovered peers from Phase 1
Edges:  derived from seed list relationships (who links to whom)
        + NADI communication pairs (who sent to whom, from envelope targets)

Node classification from capabilities (declared, not guessed):
  RELAY:       "nadi-relay" in capabilities
  GOVERNANCE:  "governance" in capabilities  
  RESEARCH:    "research_synthesis" in capabilities
  EXECUTION:   "code_analysis" or "task_execution" in capabilities
  OBSERVER:    "federation-visualization" in capabilities
  PROTOCOL:    layer == "internet"
  OUTPOST:     "authority-publishing" in capabilities
  TEMPLATE:    "test-target" in capabilities or repo_id contains "template"
  GENERIC:     none of the above match

Status from declared + observed:
  ACTIVE:       descriptor.status == "active" AND nadi_outbox reachable
  DECLARED:     descriptor.status == "active" BUT nadi_outbox unreachable
  SLEEPING:     descriptor.status != "active"
  FROZEN:       no successful fetch in 7+ days (from peers.json history)

Output: data/federation/topology.json
```

### Phase 5: Render ASCII Map

Deterministic. Pure Python string formatting. No randomness.

```
┌──────────────────────────────────────────────────────────────────┐
│                   AGENT FEDERATION — TOPOLOGY                     │
│                   Generated: 2026-07-19 15:07 UTC                 │
│                   Cycle: #1  ·  Protocol: NADI v1                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌────────────────┐                                              │
│   │ agent-internet │──── NADI RELAY (144 pending) ────┐           │
│   │ ● ACTIVE       │                                  │           │
│   │ layer: internet│                                  │           │
│   │ caps: 5        │                                  │           │
│   └────────────────┘                                  │           │
│            │                                          │           │
│   ┌────────┼──────────┬──────────┬──────────┐        │           │
│   │        │          │          │          │        │           │
│   ▼        ▼          ▼          ▼          ▼        │           │
│ ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐  │           │
│ │stewrd│ │agent-│ │steward-│ │agent-  │ │hermes- │  │           │
│ │      │ │city  │ │protocol│ │research│ │sankhya │  │           │
│ │●ACTIV│ │⍟SLEEP│ │●ACTIVE │ │●ACTIVE │ │●ACTIVE │  │           │
│ │52 NAD│ │0 NADI│ │0 NADI  │ │feed:✓  │ │caps:2  │  │           │
│ └──────┘ └──────┘ └────────┘ └────────┘ └────────┘  │           │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│ LEGEND: ● active  ⍟ sleeping  ◇ template  ◎ unreachable         │
│ NADI = pending outbox messages (communication activity)           │
│ feed = authority feed published                                   │
├──────────────────────────────────────────────────────────────────┤
│ SUMMARY: 8 nodes · 2 communicating · 1 sleeping · 0 unreachable  │
│ NADI flow: 197 pending messages across federation                 │
│ Authority feeds: 4/8 nodes publishing verified content            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Heartbeat Configuration

Offset from steward's heartbeat to avoid race conditions on NADI outbox reads:

```yaml
# .github/workflows/federation-map.yml
on:
  schedule:
    - cron: '7,22,37,52 * * * *'   # Every 15 min, offset
  workflow_dispatch:
```

---

## Identity (this node)

- **Name:** Federation Map
- **Repo:** kimeisele/federation-map
- **Tier:** Observer (passive, read-only, no mutations on other nodes)
- **Zone:** Akasha (Ether — the observation layer)
- **Layer:** visibility
- **Capabilities:** `federation-visualization`, `topology-rendering`, `health-aggregation`
- **Produces:** `topology_map`, `peer_registry`
- **Consumes:** `federation_descriptors`, `nadi_peer_identity`
- **Protocols:** `nadi-filesystem`

### Why "Observer" is a valid tier

The federation already has RELAY (agent-internet), GOVERNANCE (agent-city), RESEARCH (agent-research), EXECUTION (steward). An OBSERVER that only reads and renders is a legitimate role — it's the visibility layer the federation currently lacks.

---

## MVP Scope (POC)

### In Scope

1. `scripts/render_topology.py` — Phase 1-5, Python 3.11 stdlib only
2. Discovery from seed list (8 nodes) — `.well-known/` + `peer.json`
3. NADI outbox read from each peer → activity status
4. Authority feed check → publishing status
5. ASCII map rendered into `README.md`
6. `topology.json` + `peers.json` written to `data/federation/`
7. `.well-known/` descriptor + agent card for this node
8. GitHub Actions heartbeat (15-min cycle)
9. NADI inbox + outbox set up (receive heartbeats, send topology updates — Phase 2)

### Out of Scope (MVP)

- NADI message sending (this node is read-only in MVP, becomes active in Phase 2)
- GitHub topic search for dynamic peer discovery (use seed list only)
- Historical trend data (peers.json history)
- Reading any file not declared in the federation protocol surfaces
- Alerting (steward's Reaper handles this)

---

## Protocol Compliance

federation-map is a conformant federation node because it:

1. Exposes `.well-known/agent-federation.json` ✅
2. Has `data/federation/peer.json` with NADI identity ✅
3. Has `data/federation/nadi_outbox.json` + `nadi_inbox.json` ✅
4. Can be discovered via seed list or topic search ✅
5. Uses the same Python-stdlib-only contract ✅
6. Follows the same heartbeat pattern (15-min GitHub Actions) ✅

The only difference from other nodes: it's read-only in MVP. It observes. That's the point.

---

## Why This Approach Is Correct

1. **Protocol surfaces are stable.** `.well-known/agent-federation.json` is the contract. `peer.json` is the contract. Internal files like `steward_health.json` can change or disappear — the protocol surfaces cannot.

2. **NADI outbox count IS the health metric.** A node with 144 pending NADI messages is communicating actively. A node with 0 might be idle or sleeping. The outbox IS the pulse.

3. **The map shows what the federation declares about itself.** Not what we infer from internals. If a node says it's "active" but has 0 NADI activity for 30 days — that's visible, not hidden. The discrepancy IS the information.

4. **This scales.** Any new node that adds `.well-known/agent-federation.json` + `peer.json` automatically appears on the map. No configuration needed.

---

## Next Steps

1. [ ] Spec review (Opus)
2. [ ] Implement Phase 1: Discovery from seed list
3. [ ] First ASCII map from real `.well-known/` + `peer.json` data
4. [ ] Phase 2: NADI outbox activity check
5. [ ] Phase 3: Authority feed check
6. [ ] Phase 4: Render + commit heartbeat
7. [ ] Phase 5: NADI inbox listener (become active member)

---

*v0.1 — Initial spec, July 2026 (scraped internal files — wrong approach)*
*v0.2 — Rewritten: federation protocol surfaces only. NADI outbox = pulse. No scraping.*
