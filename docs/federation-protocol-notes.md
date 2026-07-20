# The Agent Federation + NADI — as actually implemented

Written from `kimeisele/agent-internet` source. Every claim cites file + line.

---

## 1. What is the federation?

The agent federation is **a mesh of GitHub repositories** that each expose three protocol surfaces:

| Surface | Path | Purpose |
|---------|------|---------|
| Federation Descriptor | `.well-known/agent-federation.json` | Declares membership: `kind`, `status`, `repo_id`, `capabilities`, `layer` |
| NADI Peer Identity | `data/federation/peer.json` | NADI transport identity: `identity.city_id`, `endpoint.transport`, `nadi.outbox`/`inbox` paths |
| NADI Outbox/Inbox | `data/federation/nadi_outbox.json` / `nadi_inbox.json` | Message queue. Array of `DeliveryEnvelope`. Relay pump reads outbox → delivers to target inbox. |

**Source:** `agent-internet/agent_internet/agent_city_contract.py:18-64` (filesystem contract defining all paths)
**Source:** `agent-internet/docs/FEDERATION_DESCRIPTOR_V1.md:1-77` (descriptor schema + topic discovery)

---

## 2. Discovery — how the federation finds its members

### 2.1 The real mechanism: GitHub topic search (the official way)

**Source:** `agent-internet/scripts/federation_relay_pump.py:41-63` (`_discover_peers_via_github_topic`)
**Source:** `agent-internet/docs/FEDERATION_DESCRIPTOR_V1.md:54-64` ("Topic discovery")

The relay pump's discovery stack (line 108-151):
1. **GitHub topic search** (`topic:agent-federation-node`) — primary, global discovery
2. **Filesystem beacons** — local sibling repos that announced themselves
3. **Descriptor fetch** — validates each discovered node's `.well-known/agent-federation.json`

The topic search is **not** a hack or platform dependency — it is the **documented, official discovery mechanism**. The FEDERATION_DESCRIPTOR_V1 spec explicitly says (line 54-56):

> For zero-touch discovery, add the GitHub topic: `agent-federation-node`

### 2.2 The seed list: a bootstrap cache, not the primary registry

**Source:** `agent-internet/docs/FEDERATION_DESCRIPTOR_V1.md:45-51` ("Seed-list format")

The seed list (`authority-descriptor-seeds.json`) is a JSON file that "can be either a JSON object with `descriptor_urls` or a JSON array of descriptor URLs." It is a **bootstrap fallback** — a way to seed the initial set of known nodes before topic discovery takes over.

**The seed list is NOT the authoritative member registry.** It is a stale snapshot that needs manual maintenance. The topic search is the dynamic, zero-maintenance mechanism.

### 2.3 Discovery caching

**Source:** `agent-internet/scripts/federation_relay_pump.py:37-38,85-96`

The relay pump caches discovered peers for 15 minutes (`_CACHE_TTL_S = 900`) at `data/federation/discovered_peers.json`. This avoids hitting the GitHub API every cycle while keeping discovery fresh.

### 2.4 PR #8 assessment

PR #8 (GitHub topic search in `render_topology.py`) is **correct in concept** — it implements the same mechanism the relay pump uses. However:

- **Correct:** Topic search is the official discovery method.
- **Correct:** Seeds-first fallback ensures baseline resilience when the API is down.
- **Correct:** `default_branch` from the API (not hardcoded "main") is the right behavior.
- **Missing:** The relay pump also uses **filesystem beacons** for local sibling discovery. federation-map could adopt this when running in a local clone environment.
- **Design note:** `_discover_topic()` in `render_topology.py` reimplements topic search with `urllib` instead of reusing `discover_federation_descriptors_by_github_topic` from agent-internet. This is acceptable for federation-map's stdlib-only constraint, but creates a maintenance fork of the discovery logic.

**Recommendation on PR #8: KEEP.** Topic search is the official mechanism. Demote it to last-resort only if we also implement the primary discovery path — but the topic search IS the primary path. The seed list should be demoted to bootstrap fallback, not the other way around.

**What to fix:** Rename the seed list variable or add a comment making clear that seeds are a bootstrap cache, not the authority. The topic search output should be the primary peer set, with seeds filling gaps when the API is unavailable.

---

## 3. NADI transport — how messages actually move

### 3.1 The relay pump

**Source:** `agent-internet/agent_internet/pump.py:18-88` (`OutboxRelayPump`)
**Source:** `agent-internet/agent_internet/filesystem_transport.py:30-116` (`FilesystemFederationTransport`)

The pump reads each peer's `nadi_outbox.json`, enriches messages with missing IDs, relays each envelope through the control plane, and atomically drains delivered messages:

```
1. read_outbox()        — shared lock (fcntl.LOCK_SH)
2. enrich missing IDs   — exclusive lock (fcntl.LOCK_EX) + atomic write (.tmp → rename)
3. relay each envelope  — plane.relay_envelope(DeliveryEnvelope)
4. remove_from_outbox() — exclusive lock, re-reads file, removes only delivered
```

**Source:** `agent-internet/agent_internet/file_locking.py:19-51` (atomic writes + fcntl locking)

### 3.2 Envelope schema (confirmed from live data)

**Source:** `agent-internet/agent_internet/pump.py:60-76` (DeliveryEnvelope construction)
**Source:** Live outbox fetch from `agent-internet` (144 envelopes): keys = `correlation_id, id, operation, payload, priority, source, target, timestamp, ttl_s`
**Source:** Live outbox fetch from `steward` (44 envelopes): keys = `correlation_id, operation, payload, payload_hash, priority, signature, source, target, timestamp, ttl_s`

The canonical fields in `DeliveryEnvelope` (as constructed by the pump):
- `source_city_id` — set by pump from `message["source"]` (line 59)
- `target_city_id` — set from `message["target"]` (line 63)
- `operation` — from `message["operation"]` (line 64)
- `payload` — from `message["payload"]` (line 65)
- `envelope_id` — assigned if missing (lines 37-41)
- `correlation_id` — from message (line 67)
- `ttl_s` — from message (line 69)
- `nadi_type` — transport type (line 70)
- `nadi_op` — NADI operation (line 71)
- `priority` — from `nadi_priority` (line 72)
- `ttl_ms` — from message (line 73)
- `maha_header_hex` — from message (line 74)

**Key finding for federation-map's Flow parser:** The pump reads `source` and `target` from the raw envelope, but the canonical `DeliveryEnvelope` class uses `source_city_id` and `target_city_id`. Both naming conventions exist in the ecosystem. PR #7's dual-field fix (`source or source_city_id`) is correct.

### 3.3 Transport types

**Source:** `agent-internet/agent_internet/transport.py` (TransportScheme enum)
- `FILESYSTEM` — local sibling repos (the primary transport for local development)
- `HTTPS` — remote peers via GitHub API (`github_api_transport.py`)
- `RAW` — raw.githubusercontent.com (used by federation-map)

### 3.4 Topology model

**Source:** `agent-internet/scripts/federation_relay_pump.py:181-203` (`_register_discovered_peers`)

The topology is **hub-and-spoke with bidirectional trust**:
- `agent-internet` is the relay hub
- All peers are connected to all other peers via bidirectional trust (`TrustLevel.VERIFIED`)
- Routes are published from `agent-internet` to each peer
- Messages flow: sender outbox → relay pump → target inbox
- The relay pump resolves broadcast (`target: "*"`) to unicast (line 224-233)

It is NOT a full mesh where every node talks directly to every other. It IS a relayed mesh where the pump mediates all inter-node communication, but the trust graph is fully connected.

---

## 4. Edge signals — what makes a connection strong

The protocol exposes multiple dimensions of connection strength:

### 4.1 NADI traffic volume (queue depth + direction)

**Available today.** The number of envelopes from A→B in the outbox is a direct measure of communication volume. This is what federation-map currently uses in the Flows panel.

### 4.2 Transport type

**Source:** `agent-internet/agent_internet/agent_city_contract.py:18-64`
**Available today from `peer.json`.** `transport: "filesystem"` = local, colocated. `transport: "https"` = remote. This is a structural edge property — a filesystem peer is "closer" than an HTTPS one.

### 4.3 Trust level

**Source:** `agent-internet/scripts/federation_relay_pump.py:187-194`
**Source:** `agent-internet/agent_internet/models.py` (TrustLevel enum)
Real values: `VERIFIED`, `TRUSTED`, `NEUTRAL`, `UNTRUSTED`. The relay pump grants `VERIFIED` to all discovered peers with active descriptors. Lower levels exist but are not used by default.

### 4.4 Relay/backbone role

**Source:** `agent-internet/docs/ARCHITECTURE.md:31-41`
`agent-internet` owns "routing between cities" and "trust relationships between cities." A node that also acts as a relay (e.g., `agent-internet`'s `nadi-relay` capability) is a backbone node — structurally different from a leaf node.

### 4.5 What we CANNOT get from protocol surfaces alone

- **Latency** — not exposed in any protocol surface
- **Uptime/reliability** — not exposed (would require monitoring the relay pump's delivery receipts)
- **Trust scores** — live trust values are in the Lotus control plane, not in public surfaces

---

## 5. Gap analysis — where federation-map diverges

### 5.1 Discovery (Phase 1)

| What federation-map does | What the protocol actually does | Gap |
|--------------------------|-------------------------------|-----|
| `_discover_live()` reads seed URLs from local `authority-descriptor-seeds.json` | Relay pump uses GitHub topic search as primary, seed list as bootstrap cache | PR #8 already fixes this. Topic search is correct. |
| Seed list is the primary data source | Topic search is the primary, seed list is fallback | Seeds and topic should swap priority: topic first, seeds as fill. |
| No discovery caching | Relay pump caches 15 min at `discovered_peers.json` | Minor — not critical for a 15-min render cycle, but would reduce API calls. |
| `descriptor_url` field not stored | Relay pump stores `descriptor_url` per peer | Missing — would enable re-validation. |

### 5.2 NADI outbox path (Phase 2)

| What federation-map does | What the protocol actually does | Gap |
|--------------------------|-------------------------------|-----|
| Reads outbox from `{base_url}/{peer.nadi.outbox}` | The relay pump reads outbox from local filesystem (`data/federation/nadi_outbox.json`) | federation-map reads via raw.githubusercontent.com. This works but is NOT the NADI transport — it's a read-only HTTP snapshot. |
| `base_url` uses hardcoded `"main"` from `_node_base_url()` | Relay pump uses local filesystem or GitHub API | PR #8 partially fixes this (topic peers use `default_branch`). Seed peers should use the URL to derive the branch instead of hardcoding "main". |

### 5.3 Authority feed (Phase 3)

| What federation-map does | What the protocol actually does | Gap |
|--------------------------|-------------------------------|-----|
| Checks `{repo}/authority-feed/latest-authority-manifest.json` on the `authority-feed` branch | The descriptor contains `authority_feed_manifest_url` pointing to the raw.githubusercontent.com URL | **Bug.** Should read `authority_feed_manifest_url` from the descriptor, not construct the URL ourselves. The descriptor IS the contract for where the feed lives. |
| Boolean presence check | The manifest contains artifact lists, versions, hashes | Acceptable for MVP — presence is enough for the map. |

### 5.4 Edges / flows (Phase 4)

| What federation-map does | What the protocol actually does | Gap |
|--------------------------|-------------------------------|-----|
| Flows from envelope `source`/`target` fields | Same mechanism. Dual naming conventions exist (`source_city_id`/`target_city_id` vs `source`/`target`) | PR #7 fixed this. |
| Single binary "flow" representation | Protocol has multiple edge dimensions: volume, transport type, trust level, relay role | Missing richer edge typing. |
| No bidirectional flow tracking | Relay pump tracks `source_city_id → target_city_id` per envelope | federation-map already does this — volumes per source→target pair. Correct. |

### 5.5 What federation-map gets RIGHT

- Protocol surfaces only (`.well-known/`, `peer.json`, NADI outbox) — no internal file scraping ✅
- Envelope field dual-convention fix (`source`/`target` + `source_city_id`/`target_city_id`) ✅
- Authority feed branch fix (`authority-feed` branch, not directory) ✅
- Role classification from capabilities ✅
- Terra Map territory/weather model ✅

---

## 6. Corrected design proposal

### 6.1 Discovery (revised priority)

**Current:** seeds → topic → merge
**Proposed:** topic → seeds → merge (topic is the primary, seeds fill gaps)

Rationale: The relay pump uses topic search as primary. `FEDERATION_DESCRIPTOR_V1.md` calls it "zero-touch discovery." Seeds should be a bootstrap safety net, not the primary source.

Implementation (in `_discover_live`):
```python
# Primary: topic search
topic_peers = _discover_topic()
for p in topic_peers:
    if p["repo_id"].lower() not in seen:
        seen.add(p["repo_id"].lower())
        peers.append(p)

# Fill gaps from seeds (bootstrap safety net)
for url in seed_urls:
    # ... same as current seed logic, but skip if already in peers
```

### 6.2 Authority feed path (use descriptor, don't construct URL)

**Current:** `https://raw.githubusercontent.com/{repo_id}/authority-feed/latest-authority-manifest.json`
**Proposed:** Read `authority_feed_manifest_url` from the federation descriptor. Fall back to the constructed URL only if the field is missing.

```python
def _check_authority_feed_network(base_url, repo_id):
    # Prefer the descriptor's declared URL
    manifest_url = descriptor.get("authority_feed_manifest_url", "")
    if manifest_url:
        data = _fetch_json(manifest_url)
        return isinstance(data, dict) and data.get("kind") == "source_authority_feed_manifest"
    # Fallback: construct from repo_id + authority-feed branch
    url = f"https://raw.githubusercontent.com/{repo_id}/authority-feed/latest-authority-manifest.json"
    ...
```

### 6.3 Weighted, typed edges

Instead of one binary "flow" line, represent the connection with multiple dimensions:

| Dimension | Source | Tiers |
|-----------|--------|-------|
| **Traffic volume** | NADI outbox queue depth per source→target | `·` (0), `─` (1-10), `═` (11-50), `▓` (51+) |
| **Transport proximity** | `peer.json` → `endpoint.transport` | `filesystem` = local, `https` = remote |
| **Trust level** | From relay pump trust graph (if accessible) | `verified` / `neutral` / `untrusted` |
| **Backbone role** | `nadi-relay` capability in descriptor | Relay node vs leaf node |

For the Terra Map: these dimensions directly fuel richer geography. Traffic volume → edge thickness. Transport → coastal vs deep-water connection. Trust → border style. Backbone → node elevation/size.

---

## 7. Explicit recommendation on PR #8

**KEEP the topic search.** It is the official discovery mechanism, documented in `FEDERATION_DESCRIPTOR_V1.md:54-56` and used by the relay pump (`federation_relay_pump.py:41-63`).

**Minor correction:** Swap priority — topic search should be primary, seeds should fill gaps. Currently the code does seeds-first-then-topic. This is a one-line reorder in `_discover_live()`.

**Add:** Store `authority_feed_manifest_url` from the descriptor when present, and use it in Phase 3 (see §6.2 above).

---

## 8. Open questions (not yet answerable from current source reading)

1. **Where does a new node like agent-village actually register?** The answer is: it adds the `agent-federation-node` topic and publishes `.well-known/agent-federation.json`. There is no centralized registry — the topic IS the registry. If agent-village has the topic, it will appear within 15 minutes (next relay pump cycle). If it does not, no mechanism will discover it except the manual seed list. **Current hypothesis confirmed from source.**

2. **Is there a canonical peer registry beyond topic search?** The relay pump also reads `authority-descriptor-seeds.json` and filesystem beacons. The Lotus control plane stores peer records internally. But the *public* discovery mechanism is topic search + descriptor validation. There is no single "membership.json" file anywhere.

3. **Do all nodes that have the topic also have valid descriptors?** Not guaranteed. `_discover_topic()` correctly validates `kind == agent_federation_descriptor`. Some repos may have the topic without a valid descriptor — those are not federation members.
