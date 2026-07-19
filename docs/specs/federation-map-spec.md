# Federation Map — Specification v0.3

**Status:** Draft — POC
**Goal:** A single, auto-generated ASCII **terrain map** of the live Agent Federation, committed into `README.md`. Not an org-chart of boxes — a landscape you read at a glance: where the mesh is busy, who is talking to whom, and how that changes over time. Driven only by federation protocol surfaces. No JavaScript, no web framework, no scraping of internal files.

> **Principle:** Read-only on the federation, and honest about what the data means. Every number on the map comes from a standardized surface every node exposes. We never claim a metric the protocol doesn't actually reveal.

---

## NORTH STAR

**Make the invisible federation visible — as a living landscape.** A developer, agent, or outsider opens one README and within 5 seconds sees the *shape* of the federation: which layers are mountains of activity, which are sleeping flatland, who is sending to whom, and whether the mesh is rising or eroding since the last cycle.

The README is **one frame.** The git history is the **time-lapse** — `git log -p README.md` is a flipbook of the federation breathing. We get animation for free, versioned and unfalsifiable, without a second file.

---

## What changed (v0.2 → v0.3)

v0.2 fixed the right thing: it stopped scraping internal files (`steward_health.json`, `CLAUDE.md`, `pokedex.json`) and moved to protocol surfaces only. That decision stands.

But v0.2 still drew the wrong artifact. Three corrections define v0.3:

1. **From diagram to map.** v0.1/v0.2 render a hand-authored box-and-arrow graph. Auto-drawing that shape for 8 nodes *and* degrading it cleanly to 40 is a graph-drawing / edge-routing problem — the exact part that becomes ASCII spaghetti at scale, and the exact "overkill" we don't want. Worse: in that layout a node's **position means nothing**. A real map encodes meaning in position. v0.3 renders a **terrain**: vertical position = layer/zone, elevation/shade = live activity. Position and height both carry information. Rendering is binning + row layout, not edge routing.

2. **Edges come from envelopes, not the seed list.** v0.2 says edges are "derived from seed list relationships." The seed list is a flat array — it has no "who links to whom." The real directed graph is already sitting in each node's NADI outbox: every `DeliveryEnvelope` carries `source_city_id` and `target_city_id` (see this repo's own `scripts/nadi_send.py`). Reading envelope *targets* gives a real, directed, weighted "who talks to whom." That is the gold v0.2 buried in a single clause.

3. **Honest metrics + a time axis.** "NADI outbox count = health" is half-wrong (see the metric contract below). And a snapshot re-rendered every 15 min shows *change* only if a human diffs it. v0.3 adds a thin, capped history file so the map shows **deltas and trends** (sparklines), which is what "Entwicklungen" actually means.

---

## What This Is NOT

- ❌ A scraper that reads arbitrary internal files from other repos
- ❌ A box-and-arrow topology graph with auto-routed ASCII edges
- ❌ A replacement for steward's Reaper or Health-Observer
- ❌ A web app, dashboard, or hosted service
- ❌ A monitor that invents metrics the protocol doesn't expose

## What This IS

- ✅ A federation node (built from agent-template), read-only in MVP
- ✅ A passive observer that reads federation-standard surfaces only
- ✅ One ASCII **terrain map** rendered into `README.md`
- ✅ Structured data (`topology.json`, `peers.json`, `history.jsonl`) for agent consumption
- ✅ A GitHub Actions heartbeat on the federation's own rhythm
- ✅ The public face of the federation — the thing you send someone to say "look, it's alive"

---

## Federation Protocol Surfaces (the only data paths we use)

Every number on the map traces back to one of these. Nothing else is read.

### Layer 1 — Discovery & Identity (every node MUST expose)

| Surface | Path | What It Declares |
|---------|------|-----------------|
| Federation Descriptor | `.well-known/agent-federation.json` | `kind`, `status`, `repo_id`, `layer`, `capabilities`, `endpoints` |
| NADI Peer Identity | `data/federation/peer.json` | `identity.city_id`, `identity.repo`, `endpoint.transport`, `capabilities`, `nadi.outbox`/`inbox` paths |

Verified 2026-07-19: 8/8 seed nodes expose the descriptor; 8/8 expose `peer.json`.

### Layer 2 — Communication (NADI transport) — **the edge source**

| Surface | Path | What It Shows |
|---------|------|--------------|
| NADI Outbox | `data/federation/nadi_outbox.json` | Array of `DeliveryEnvelope`. **Count** = queue depth. **`target_city_id` per envelope** = directed edges. |
| NADI Inbox *(optional)* | `data/federation/nadi_inbox.json` | Received messages. Even more ephemeral than the outbox; outbox targets are the better edge source. |

Observed: agent-internet ~144 pending, steward ~52, agent-city 0. We use both the **depth** (as queue pressure) and the **targets** (as edges).

### Layer 3 — Verified Content (Authority Feed)

| Surface | Path | What It Shows |
|---------|------|--------------|
| Authority Manifest | `authority-feed/latest-authority-manifest.json` | `kind == source_authority_feed_manifest` — node publishes verifiable content. |

Observed: 4/8 nodes publish an authority feed.

### Layer 4 — Peer Discovery (bootstrap)

| Surface | Source | What It Shows |
|---------|--------|--------------|
| Seed List | `data/federation/authority-descriptor-seeds.json` | Bootstrap descriptor URLs (currently 8) |
| GitHub Topic Search *(post-MVP)* | `agent-federation-node` topic | Dynamic discovery of new nodes |

This is the same mechanism `scripts/discover_federation_peers.py` already uses. federation-map reuses it, doesn't reinvent it.

### What we deliberately do NOT read

`CLAUDE.md`, `steward_health.json`, `pokedex.json`, or any path not declared in a node's `.well-known/agent-federation.json` / `peer.json`. Those files hold valuable data — the correct way to surface it is for those nodes to publish it via their authority feed or answer a NADI query. That's protocol evolution, not a scraping shortcut.

---

## The Honest Metric Contract

This is the section that keeps the map from becoming bullshit. For every metric we render, we state what it **means** and — just as important — what it does **not** mean.

| Metric | Surface | Honestly means | Does NOT mean |
|--------|---------|----------------|---------------|
| **NADI queue depth** | outbox length | Messages *not yet delivered* — backpressure / queue depth | "Health." High can mean *busy* OR *relay jammed*. A fast relay drains and reads *low*. |
| **Flow volume** | count of envelopes by `target_city_id` | Real directed communication seen this cycle | Total lifetime traffic (outbox is ephemeral — it's a snapshot) |
| **Depth trend (Δ)** | queue depth vs. history | Rising = producing faster than draining; falling = draining | Absolute activity — read alongside flow volume |
| **Monotonic growth** | depth ↑ for N cycles | **Relay stall / jam** — an actionable signal | Node health per se — but worth surfacing loudly |
| **Declared status** | descriptor `status` | What the node *claims* about itself | Ground-truth liveness (that's the *observed* column) |
| **Observed reachability** | did the surface fetch succeed | Whether we could read the node this cycle | Whether the node is doing useful work |
| **Authority feed present** | manifest fetch | Node publishes verifiable content | Content is fresh or correct (MVP checks presence only) |
| **Layer / capabilities** | descriptor | The node's declared role in the mesh | Anything we inferred or guessed |

Two consequences we lean into:

- **Activity = flow volume + depth trend, not raw depth.** A node draining fast looks low-depth but is very active; flow volume catches that.
- **The discrepancy is the information.** A node that declares `active` but shows 0 flow for many cycles is *rendered as such* — `DECLARED` status, flat terrain. We don't hide the gap; we draw it.

---

## The Map: three panels, all lists, no edge routing

The whole artifact is three stacked panels. Each is fundamentally a **list**, so each scales by getting taller — never by solving a layout. This is the deliberate anti-overkill choice.

### Panel A — TERRAIN (the core)

Nodes placed by **layer/zone** (vertical position = where in the stack). Elevation/shade = live activity, binned into `· ░ ▒ ▓ █`. You read the landscape: a range in the relay layer, hills among the citizens, desert where nodes sleep.

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #128 · 2026-07-19 15:07Z   │
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high   │
├──────────────────────────────────────────────────────────────────────┤
│  AKASHA · observation                                                  │
│    ◇ federation-map          ─────   observer · sea level              │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  INTERNET · relay/transport                                            │
│    █ agent-internet          ▇▇▇▅▂   144  ↑   relaying                 │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  PROTOCOL · governance/authority                                       │
│    ▒ steward-protocol        ▁▁▁▁▁     0      feed✓                    │
│    ░ hermes-sankhya          ▁▂▁▁▁     2      feed✓                    │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  NODE · execution/citizens                                             │
│    ▓ steward                 ▅▄▆▇▅    52  ↑   feed✓                    │
│    ▒ agent-research          ▂▁▃▂▁     3      feed✓                    │
│    ░ agent-world             ▁▁▂▁▁     1                               │
│    · agent-city              ▁▁▁▁▁     0      sleeping                 │
│    ◇ steward-test            ─────     —      template                 │
└──────────────────────────────────────────────────────────────────────┘
```

Glyph = status/shade, then a **sparkline** (depth over last ~5 cycles), current depth, trend arrow, and flags. Adding a node adds a row. That's the entire scaling story for Panel A.

### Panel B — FLOWS (who talks to whom, for real)

Directed edges from actual `target_city_id` values in each outbox, ranked by volume. This *is* the relationship view — without faking a planar graph.

```
  FEDERATION FLOWS · directed, from live NADI envelopes (cycle #128)
    agent-internet ──▶ steward          88  ▇▇▇▇
    agent-internet ──▶ agent-research   41  ▇▇
    steward        ──▶ agent-city       12  ▇
    steward        ──▶ agent-internet    9  ▇
    silent: agent-world, steward-test, hermes-sankhya
```

At scale: show top-N flows + "＋K more", or switch to an **adjacency matrix** (N×N glyph grid) — the scalable ASCII answer for connectivity up to ~24 nodes. Beyond that, aggregate flows by zone.

### Panel C — PULSE (federation-wide, over time)

```
  FEDERATION PULSE
    nodes         8   ▁▁▁▁▁  steady
    active        6   ▅▅▆▆▆   ↑
    in flight   197   ▂▄▆▇█   ↑ 34% vs. last cycle
    feeds       4/8   ▁▁▁▁▁  steady
    busiest    agent-internet · 144 pending  (↑ 12 cycles — relay backlog?)
    quietest   agent-city · 0 msgs / 6 cycles
```

The `busiest` line demonstrates the free operational signal: monotonic backlog growth surfaced as a question, not hidden.

---

## Time dimension

`data/federation/history.jsonl` — one compact line per cycle, appended, **capped at the last 96 lines (~24h)**:

```json
{"ts":"2026-07-19T15:07Z","cycle":128,"depth":{"agent-internet":144,"steward":52},"active":6,"in_flight":197,"flows":{"agent-internet>steward":88}}
```

Sparklines read the last 5–8 points. No database, no trend engine, ~1 KB/cycle. The 15-min heartbeat + git history together are the long-term record; `history.jsonl` is only the short window the current frame needs.

---

## Architecture

```
federation-map/
├── .well-known/
│   ├── agent-federation.json       ← this node's federation identity
│   └── agent.json                  ← this node's agent card
├── data/federation/
│   ├── peer.json                   ← this node's NADI identity
│   ├── peers.json                  ← discovered peer registry (seeds [+ topic search])
│   ├── topology.json               ← computed: nodes + status + flows (source of truth)
│   ├── history.jsonl               ← capped short-window history for sparklines/deltas
│   ├── nadi_outbox.json            ← this node's outbox (read-only in MVP)
│   └── nadi_inbox.json             ← this node's inbox (post-MVP listener)
├── scripts/
│   ├── discover_federation_peers.py  ← EXISTS — reuse (seeds + topic search)
│   ├── federation_utils.py           ← EXISTS — fetch helpers (see note below)
│   └── render_topology.py            ← THE CORE: read surfaces → compute → render
├── docs/specs/federation-map-spec.md
├── README.md                        ← contains the live terrain map (auto-committed)
└── .github/workflows/federation-map.yml
```

**Note on the fetch layer (real inconsistency to resolve):** this spec claims "stdlib only," but the existing `federation_utils.curl_json` shells out to `curl` via `subprocess`. Pick one and be consistent. Tech-lead call: `render_topology.py` uses **`urllib.request`** (true stdlib, zero external binary), and we migrate `federation_utils` to urllib in the same PR — or, if the federation contract prefers `curl` everywhere, drop the "stdlib urllib" wording. Do not ship a spec that says urllib while the code shells out to curl.

---

## The Core Script: `scripts/render_topology.py`

Python 3.11, standard library only (`urllib.request`, `json`, `hashlib`, `datetime`). Deterministic: same inputs → byte-identical output (except the timestamp, which is isolated — see commit gating).

### Phase 1 — Discover peers
Read seed URLs → fetch each `.well-known/agent-federation.json` → validate `kind == agent_federation_descriptor` → also fetch `peer.json` → dedupe by `repo_id`. Reuse `discover_federation_peers.py`. Output: `peers.json`.

### Phase 2 — Read communication
For each peer's declared `nadi.outbox` path: fetch it, count envelopes (**queue depth**), and extract `target_city_id` per envelope (**flows**). Record depth + directed flow counts.

### Phase 3 — Read authority feed
Try `authority-feed/latest-authority-manifest.json`. Record `has_authority_feed`.

### Phase 4 — Compute topology
- **Nodes**: all discovered peers.
- **Status** (declared ∧ observed):
  - `ACTIVE` — declares active AND outbox reachable
  - `DECLARED` — declares active BUT outbox unreachable / 0 flow for N cycles
  - `SLEEPING` — declares non-active
  - `UNREACHABLE` — no surface fetch succeeded this cycle
  - `FROZEN` — no successful fetch in 7+ days (from `history.jsonl`)
- **Role** from declared capabilities (never guessed): `RELAY` / `GOVERNANCE` / `RESEARCH` / `EXECUTION` / `OBSERVER` / `PROTOCOL` (layer==internet) / `OUTPOST` / `TEMPLATE` / `GENERIC`.
- **Edges** from Phase 2 flow counts (directed, weighted). No seed-list pseudo-edges.
- Append this cycle to `history.jsonl`; trim to 96 lines.
- Output: `topology.json` (the source of truth; the ASCII is a rendered view).

### Phase 5 — Render
Terrain (Panel A) + Flows (Panel B) + Pulse (Panel C) into the `README.md` region between `<!-- federation-map:start -->` / `<!-- federation-map:end -->`.

---

## Determinism & Scaling (no layout solver, ever)

1. **No force-directed layout. No auto-routed edges.** Panel A is grouped rows; Panel B is a ranked list / matrix.
2. **Everything scales by height.** 8 nodes or 40: more rows, same code. Zones can collapse to a summary line at large N.
3. **Detail tiers inside a row**, not via a second layout: at large N drop the sparkline, keep glyph + depth.
4. **Connectivity at scale** = adjacency matrix (glyph grid) up to ~24 nodes; beyond that, zone-aggregated flows.
5. **`topology.json` is the source of truth.** Any agent reads it without parsing ASCII.

---

## Heartbeat & commit hygiene

```yaml
# .github/workflows/federation-map.yml
on:
  schedule:
    - cron: '7,22,37,52 * * * *'   # every 15 min, offset from steward
  workflow_dispatch:
```

**Commit-churn (carried from v0.1, must be handled):** a naïve render rewrites the timestamp every cycle → a commit every 15 min forever (~96/day) even when nothing meaningful changed. Gate it:

- Compute a content hash of `topology.json` **excluding** the `generated_at` field.
- Commit only if the hash changed since the last cycle **or** every Nth cycle (a low-rate "still alive" heartbeat, e.g. hourly).
- This repo already has **four** committing workflows (discovery, agent-card sync, descriptor sync, authority feed). A fifth every-15-min committer raises push-race odds → the job does `git pull --rebase origin <branch>` before pushing, and uses the standard push-retry with backoff.

---

## Identity (this node)

- **Name:** Federation Map · **Repo:** kimeisele/federation-map
- **Tier:** Observer (read-only visibility layer) · **Zone:** Akasha (Ether) · **Layer:** visibility
- **Capabilities:** `federation-visualization`, `topology-rendering`, `health-aggregation`
- **Produces:** `topology_map`, `peer_registry` · **Consumes:** `federation_descriptor`, `nadi_peer_identity`
- **Protocols:** `nadi-filesystem`, `https-raw`

"Observer" is a legitimate role — the federation has RELAY, GOVERNANCE, RESEARCH, EXECUTION; it lacks a visibility layer. One read-only node that renders is exactly that. (No further justification needed.)

---

## MVP Scope (POC)

### In scope
1. `scripts/render_topology.py` — Phases 1–5, stdlib only.
2. Discovery from the seed list (8 nodes): `.well-known/` + `peer.json`.
3. NADI outbox read per peer → **queue depth + flow edges** (`target_city_id`).
4. Authority-feed presence check.
5. **Panel A (Terrain)** + **Panel C (Pulse)** rendered into `README.md`.
6. `topology.json` written; `history.jsonl` appended + capped.
7. `.well-known/` descriptor + agent card for this node (exist).
8. GitHub Actions heartbeat with commit-hash gating + rebase-before-push.

### Fast-follow (next PR, still cheap)
- **Panel B (Flows)** list — depends on confirming the envelope shape (see risks).
- Sparklines fill in once `history.jsonl` has a few cycles.

### Out of scope (MVP)
- Sending NADI messages (read-only in MVP; active member later).
- GitHub topic search for dynamic discovery (seed list only for now).
- Adjacency matrix / >24-node zone aggregation (not needed at 8).
- Reading any non-protocol surface.
- Alerting (steward's Reaper owns this; we only *surface* the backlog signal).

---

## Open questions & risks (resolve before/while coding)

1. **Envelope shape — must verify (the v0.1-style trap).** Panel B and flow edges assume other nodes' outboxes carry `target_city_id`/`source_city_id` like this repo's `nadi_send.py`. Likely true (shared agent-template), but unconfirmed. **Recon step (≈3 `curl`s, not a build):** inspect 2–3 real outboxes — agent-internet (~144) is the ideal sample — plus one `peer.json`, and confirm the field names before building flows. If the shape differs, adjust the extractor, not the concept.
2. **Depth semantics.** Confirm whether a high outbox reflects active sending or relay backlog for the specific relay node, so the Pulse "backlog?" heuristic is tuned to a real threshold, not a guess.
3. **urllib vs curl.** Decide the fetch layer (above) in this PR; don't leave the spec and code disagreeing.
4. **Sandbox note for reviewers.** Some environments (e.g. web sessions behind a network policy) cannot reach `raw.githubusercontent.com`; validate the renderer in GitHub Actions, where raw access works.

---

## Next steps
1. [x] Spec review → v0.3 (this document)
2. [ ] Recon: confirm envelope + peer.json field shapes on 2–3 live nodes
3. [ ] Implement Phase 1 (discovery) + Phase 4/5 Terrain from `.well-known` + `peer.json`
4. [ ] Add Phase 2 depth + Pulse panel
5. [ ] Add `history.jsonl` + sparklines
6. [ ] Add Panel B (Flows) once envelope shape is confirmed
7. [ ] Heartbeat with commit-hash gating + rebase-before-push
8. [ ] (Later) NADI inbox listener → become an active member

---

*v0.1 — Initial spec (scraped internal files — wrong data source).*
*v0.2 — Rewritten: federation protocol surfaces only. NADI outbox = pulse. No scraping.*
*v0.3 — Reframed: terrain map, not box-graph (position & elevation carry meaning). Edges from real NADI envelope targets, not the seed list. Honest metric contract (queue depth ≠ health). Time axis via capped `history.jsonl` + git history. Scaling by lists/rows, never edge-routing. Commit-churn gating + fetch-layer (urllib) consistency called out.*
