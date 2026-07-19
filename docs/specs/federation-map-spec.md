# Federation Map — Specification v0.1

**Status:** Draft — POC
**Goal:** A single-file, auto-generated, ASCII-art topology map of the live Agent Federation. No JavaScript. No web framework. No gimmicks. One README that shows the federation breathing.

> **Principle:** Read-only on the federation. This repo only writes its own data. Every metric comes from a real, fetchable URL on an existing federation node.

---

## NORTH STAR

**Make the invisible federation visible.** A new developer — or any federation agent — should be able to open one README and see within 5 seconds: who is alive, who is talking to whom, and what the health of the mesh is.

No dashboards. No Grafana. No login. `curl`-able. `git clone`-able. Agent-parseable.

---

## What This Is NOT

- ❌ A monitoring service with alerts
- ❌ A replacement for steward's Reaper or Health-Observer
- ❌ A web app, dashboard, or hosted service
- ❌ A modification to any existing federation node
- ❌ A gimmick that generates pretty pictures from fake data

## What This IS

- ✅ A federation node (forked from agent-template pattern)
- ✅ A deterministic script that fetches real data from real peers
- ✅ One ASCII-art map rendered into a Markdown file
- ✅ One structured data file (JSON) for agent consumption
- ✅ A GitHub Actions heartbeat that regenerates on schedule
- ✅ A public face for the federation

---

## Data Sources (all read-only, all exist today)

### Tier 1 — Always Available (every federation node has these)

| Source | URL Pattern | What It Provides |
|--------|-------------|-----------------|
| Federation Descriptor | `{repo}/main/.well-known/agent-federation.json` | `kind`, `status`, `repo_id`, `layer`, `capabilities`, `endpoints` |
| Agent Card | `{repo}/main/.well-known/agent.json` | `name`, `skills`, `provider`, `federation.interfaces` |
| Peer Identity | `{repo}/main/data/federation/peer.json` | `identity.city_id`, `identity.repo`, `endpoint.transport`, `capabilities`, `nadi` config |
| README | `{repo}/main/README.md` | Human-readable identity, purpose, status notes |

### Tier 2 — Available on Active Nodes (opt-in, but steward has it)

| Source | URL Pattern | What It Provides |
|--------|-------------|-----------------|
| Health Snapshot | `steward/main/data/federation/steward_health.json` | `peers.alive/suspect/dead/total`, `immune.*`, `gateway.*`, `cognition.*` |
| Reaper Stats | `steward/main/.steward/peers.json` | `total_reaps`, `total_evictions`, `lease_ttl_s`, `trust_decay` |
| Live Status | `steward/main/CLAUDE.md` | `Health score (sattva/rajas/tamas)`, `Federation: N peers`, task queue |
| Pokedex | `agent-city/main/data/pokedex.json` | `total` agents, `census_date`, agent list with elements/zones |

### Tier 3 — GitHub API (requires token, rate-limited)

| Source | API Endpoint | What It Provides |
|--------|-------------|-----------------|
| Workflow Runs | `GET /repos/{owner}/{repo}/actions/workflows/{id}/runs` | Last heartbeat timestamp, success/failure, run duration |
| Commit Activity | `GET /repos/{owner}/{repo}/commits` | Last commit date, commit frequency |
| Issue Activity | `GET /repos/{owner}/{repo}/issues` | Open/closed issues, discussion activity |

### Seed List (discovery bootstrap)

The authoritative seed list lives at:
`hermes-sankhya-25/main/data/federation/authority-descriptor-seeds.json`

Currently 8 seeds. The map script reads this first, then can optionally do GitHub topic search for `agent-federation-node` to discover new peers.

---

## Architecture

```
federation-map/
├── .well-known/
│   ├── agent-federation.json       ← Generated: this node's identity
│   └── agent.json                  ← Generated: this node's agent card
├── data/
│   └── federation/
│       ├── peer.json               ← This node's peer identity
│       ├── peers.json              ← Aggregate peer registry (from seeds + discovery)
│       ├── topology.json           ← Computed topology data (nodes + edges)
│       ├── health_snapshot.json    ← Latest health metrics from all reachable peers
│       └── nadi_outbox.json        ← NADI transport (for federation communication)
├── scripts/
│   └── render_topology.py          ← THE CORE: fetches data → computes → renders ASCII
├── docs/
│   └── specs/
│       └── federation-map-spec.md  ← This file
├── README.md                       ← = topology.ascii (auto-generated, committed by heartbeat)
└── .github/
    └── workflows/
        └── federation-map.yml      ← Heartbeat: runs render_topology.py, commits result
```

---

## The Core Script: `scripts/render_topology.py`

### Phase 1: Discover

```
1. Read seed list from hermes-sankhya-25 (or local copy)
2. Fetch .well-known/agent-federation.json from each seed
3. For each seed: fetch agent.json, peer.json (if available)
4. Optionally: GitHub topic search "agent-federation-node" → merge with seeds
5. Output: peers.json (deduplicated, enriched)
```

### Phase 2: Health Check

```
1. For each peer with a known data/federation path:
   - Try to fetch health data (steward_health.json or equivalent)
   - Try to fetch CLAUDE.md for the Status line
2. For each peer via GitHub API (optional, if GITHUB_TOKEN set):
   - Last workflow run timestamp → heartbeat freshness
   - Last commit timestamp → activity level
3. Output: health_snapshot.json
```

### Phase 3: Compute Topology

```
1. Nodes = unique peers from Phase 1 + Phase 2
2. Edges = NADI connections deduced from:
   - peer.json → nadi.outbox/inbox paths
   - steward_health.json → gateway stats
   - authority-descriptor-seeds.json → seed relationships
3. Node status from health data:
   - ACTIVE: heartbeat < 1h ago
   - IDLE: heartbeat 1-24h ago
   - STALE: heartbeat 1-7d ago
   - FROZEN: heartbeat > 7d or no data
   - UNKNOWN: never seen
4. Node role from capabilities + layer:
   - RELAY: has nadi-relay capability
   - GOVERNANCE: has governance capability
   - RESEARCH: has research_* capabilities
   - EXECUTION: has code_analysis, task_execution, ci_automation
   - OUTPOST: has authority-publishing, inquiry-response
   - TEMPLATE: repo_id contains "template"
   - PROTOCOL: layer = "internet" or has protocol capabilities
5. Output: topology.json
```

### Phase 4: Render ASCII Map

Deterministic layout. No randomness. Pure Python stdlib.

The map MUST include:
- **Header**: generation timestamp, total nodes, health summary
- **Topology diagram**: ASCII-drawn graph with node boxes and connections
- **Legend**: status symbols and what they mean
- **Metrics panel**: key numbers (peers alive, NADI messages, immune status)
- **Footer**: data freshness (when each source was last fetched)

Node box format (scalable — same format for 8 or 80 nodes):
```
┌──────────────────────┐
│ steward              │
│ SUPER AGENT          │
│ ● ACTIVE             │
│ HP: 5980 · ⬆23 NADI │
│ Trust: 0.86 sattva   │
└──────────────────────┘
```

---

## The Output File: `topology.ascii`

This is THE artifact. It gets embedded in README.md between marker comments:

```markdown
# Federation Map

<!-- federation-map:start -->
[ASCII map content here — auto-generated, do not edit manually]
<!-- federation-map:end -->

## Data Freshness

Last generated: 2026-07-19T14:33:00Z
Sources fetched: 8/8 descriptors, 3/3 health files, 2/2 pokedex
GitHub API: rate limit 4998/5000
```

---

## Scalability Design

The map MUST work for 8 nodes AND 80 nodes. Design decisions:

1. **Grid layout, not force-directed.** For ≤12 nodes: single-row or 2-row layout. For >12: compact grid (4 columns, N rows). Predictable positions, no overlap.

2. **Node detail is tiered.** At >20 nodes, box format compresses:
   ```
   ┌──────────────────────┐   →   │ steward ● HP:5980 │
   │ steward              │
   │ ● ACTIVE  HP: 5980   │
   └──────────────────────┘
   ```

3. **Edges are only shown for active NADI traffic.** If no traffic data available, show seed-list relationships as dotted lines. If traffic > threshold (from gateway stats), show solid lines.

4. **The JSON data files are the source of truth.** The ASCII map is a RENDERED VIEW. Any agent can read `topology.json` and `health_snapshot.json` without parsing ASCII art.

---

## Heartbeat Configuration

```yaml
# .github/workflows/federation-map.yml
name: Federation Map Refresh
on:
  schedule:
    - cron: '7,22,37,52 * * * *'   # Every 15 min, offset from steward
  workflow_dispatch:                # Manual trigger
jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python scripts/render_topology.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Optional, for API enrichment
      - run: |
          git config user.name "federation-map[bot]"
          git config user.email "federation-map[bot]@users.noreply.github.com"
          git add README.md data/
          git diff --staged --quiet || git commit -m "chore: federation map refresh [skip ci]"
          git push
```

---

## Identity

This node is itself a federation member:

- **Name:** Federation Map
- **Repo:** kimeisele/federation-map
- **Tier:** Observer (new tier — passive, read-only, no mutations)
- **Zone:** Akasha (Ether — the observation layer, the space between nodes)
- **Layer:** visibility
- **Capabilities:** `federation-visualization`, `topology-rendering`, `health-aggregation`
- **Produces:** `topology_map`, `health_snapshot`, `peer_registry`
- **Consumes:** `federation_descriptors`, `agent_cards`, `health_data`

### Federation Interfaces

```json
{
  "produces": ["topology_map", "health_snapshot", "peer_registry"],
  "consumes": ["federation_descriptor", "agent_card", "health_data", "peer_identity"],
  "protocols": ["nadi-filesystem", "https-raw"],
  "transport": "github-raw-content + nadi-outbox"
}
```

---

## MVP Scope (POC)

### In Scope

1. `scripts/render_topology.py` — Python 3.11, stdlib only (urllib + json)
2. Fetches from seed list (8 nodes)
3. Reads `.well-known/agent-federation.json` from each
4. Reads steward's `steward_health.json` for live metrics
5. Reads steward's `CLAUDE.md` for the Status line
6. Reads agent-city's `pokedex.json` for population count
7. Generates `topology.ascii` with all nodes
8. Generates `topology.json` and `health_snapshot.json` in `data/`
9. Embeds into `README.md`
10. GitHub Actions heartbeat (every 15 min, offset from steward)
11. `.well-known/` descriptor + agent card for this node

### Out of Scope (MVP)

- GitHub API enrichment (workflow runs, commit timestamps)
- GitHub topic search for dynamic peer discovery
- NADI outbox sending (this node is read-only initially)
- Historical trend data
- Alerting or anomaly detection (steward does this already)
- Multi-layout rendering (grid only for now)
- Edge/connection rendering beyond seed-list relationships

---

## Metrics That Matter (not bullshit)

Every number on the map must come from a real data source:

| Metric | Source | Why It Matters |
|--------|--------|---------------|
| Nodes total | seeds + discovery | Federation size |
| Nodes alive | steward health peers.alive | Real reachability |
| Heartbeat count | CLAUDE.md or .steward/health | Operational longevity |
| NADI messages | steward health gateway.total_requests | Inter-node communication |
| Immune heals | steward health immune.heals_attempted | Self-repair activity |
| Total reaps/evictions | steward .steward/peers.json | Network GC health |
| Agent population | agent-city pokedex.json total | Citizen count |
| Census date | agent-city pokedex.json census_date | Data freshness |
| Cognition calls | steward health cognition.total_calls | LLM usage (should be low) |
| Health score | CLAUDE.md Status line | Overall node health |

---

## Next Steps

1. [ ] Spec review and approval
2. [ ] Create repo `kimeisele/federation-map` on GitHub
3. [ ] Implement `scripts/render_topology.py` (Phase 1: Discovery only)
4. [ ] First ASCII map with real data from 8 seeds
5. [ ] Add steward health metrics (Phase 2)
6. [ ] Add agent-city pokedex data
7. [ ] GitHub Actions heartbeat
8. [ ] `.well-known/` descriptor + agent card
9. [ ] Phase 3: NADI outbox (become an active federation member)
10. [ ] Phase 4: GitHub API enrichment

---

*v0.1 — Initial spec, July 2026*
