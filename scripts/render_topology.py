#!/usr/bin/env python3
"""Render a federation terrain map from protocol surfaces.

Reads .well-known/agent-federation.json, data/federation/peer.json, and
data/federation/nadi_outbox.json from every seed peer, computes a topology,
and renders an ASCII terrain map into README.md.

Usage:
    python scripts/render_topology.py                          # live (network)
    python scripts/render_topology.py --fixtures tests/fixtures  # offline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS_PATH = REPO_ROOT / "data" / "federation" / "authority-descriptor-seeds.json"
README_PATH = REPO_ROOT / "README.md"
DATA_DIR = REPO_ROOT / "data" / "federation"
PEERS_PATH = DATA_DIR / "peers.json"
TOPOLOGY_PATH = DATA_DIR / "topology.json"
HISTORY_PATH = DATA_DIR / "history.jsonl"
NEEDS_COMMIT = DATA_DIR / ".needs_commit"
LAST_HASH = DATA_DIR / ".last_topology_hash"
HISTORY_CAP = 96

MARKER_START = "<!-- federation-map:start -->"
MARKER_END = "<!-- federation-map:end -->"

HTTP_TIMEOUT = 15
_USER_AGENT = "federation-map/0.1 (observer node)"

# ── Fetch helpers (stdlib urllib, no curl) ──────────────────────────


def _fetch_json(url: str) -> dict | list | None:
    """Fetch and parse JSON. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_text(url: str) -> str | None:
    """Fetch raw text. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


# ── Fixtures loader (offline mode) ──────────────────────────────────


class FixturesLoader:
    """Load peer surfaces from a local fixtures directory."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def list_nodes(self) -> list[str]:
        nodes: list[str] = []
        if not self._root.is_dir():
            return nodes
        for child in sorted(self._root.iterdir()):
            if child.is_dir() and (child / "agent-federation.json").exists():
                nodes.append(child.name)
        return nodes

    def load_json(self, node: str, filename: str) -> dict | list | None:
        path = self._root / node / filename
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None


# ── Phase 1: Discovery ──────────────────────────────────────────────

_TOPIC = "agent-federation-node"
_SEARCH_API = "https://api.github.com/search/repositories"
_SEARCH_PER_PAGE = 100
_SELF_REPO = "kimeisele/federation-map"


def _repo_id_to_node_name(repo_id: str) -> str:
    return repo_id.split("/")[-1]


def _node_base_url(repo_id: str, default_branch: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{repo_id}/{default_branch}"


def _fetch_json_with_headers(url: str, headers: dict) -> dict | list | None:
    """Fetch JSON with custom headers. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _discover_topic() -> list[dict]:
    """Discover peers via GitHub topic search (urllib, stdlib only).

    Returns peers from repos tagged 'agent-federation-node'.
    Graceful: on any failure, returns empty list — caller falls back to seeds.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = f"topic:{_TOPIC}"
    all_items: list[dict] = []
    page = 1

    while True:
        url = f"{_SEARCH_API}?q={query}&per_page={_SEARCH_PER_PAGE}&page={page}"
        data = _fetch_json_with_headers(url, headers)
        if not isinstance(data, dict):
            break
        items = data.get("items")
        if not isinstance(items, list):
            break
        all_items.extend(items)
        if len(all_items) >= int(data.get("total_count", 0)):
            break
        if len(items) < _SEARCH_PER_PAGE:
            break
        page += 1

    if not all_items:
        return []

    peers: list[dict] = []
    for repo in all_items:
        full_name = str(repo.get("full_name", ""))
        if not full_name:
            continue
        if full_name.lower() == _SELF_REPO:
            continue
        default_branch = str(repo.get("default_branch", "main"))
        base = _node_base_url(full_name, default_branch)

        # Fetch descriptor
        desc_url = f"{base}/.well-known/agent-federation.json"
        descriptor = _fetch_json(desc_url)
        if not descriptor or not isinstance(descriptor, dict):
            continue
        if descriptor.get("kind") != "agent_federation_descriptor":
            continue

        repo_id = str(descriptor.get("repo_id", full_name))
        node_name = _repo_id_to_node_name(repo_id)

        # Fetch peer.json
        peer_url = f"{base}/data/federation/peer.json"
        peer_data = _fetch_json(peer_url)
        peer = peer_data if isinstance(peer_data, dict) else None

        peers.append({
            "node_name": node_name, "repo_id": repo_id,
            "descriptor": descriptor, "peer": peer, "base_url": base,
            "discovery_method": "topic",
            "default_branch": default_branch,
        })

    return peers


def _discover_live(seed_urls: list[str]) -> list[dict]:
    """Discover peers: seeds first, then GitHub topic search. Deduplicated."""
    peers: list[dict] = []
    seen: set[str] = set()

    # ── Seeds first (guaranteed core, no auth needed) ────────────────
    for url in seed_urls:
        descriptor = _fetch_json(url)
        if not descriptor or not isinstance(descriptor, dict):
            continue
        if descriptor.get("kind") != "agent_federation_descriptor":
            continue
        repo_id = str(descriptor.get("repo_id", ""))
        if not repo_id or repo_id.lower() in seen:
            continue
        seen.add(repo_id.lower())

        node_name = _repo_id_to_node_name(repo_id)
        base = _node_base_url(repo_id, "main")
        peer_url = f"{base}/data/federation/peer.json"
        peer_data = _fetch_json(peer_url)
        peer = peer_data if isinstance(peer_data, dict) else None

        peers.append({
            "node_name": node_name, "repo_id": repo_id,
            "descriptor": descriptor, "peer": peer, "base_url": base,
            "discovery_method": "seed",
        })

    # ── Then topic search (dynamic discovery) ────────────────────────
    try:
        topic_peers = _discover_topic()
    except Exception as e:
        print(f"Topic discovery failed (continuing with seeds only): {e}",
              file=sys.stderr)
        topic_peers = []

    for p in topic_peers:
        repo_lower = p["repo_id"].lower()
        if repo_lower not in seen:
            seen.add(repo_lower)
            peers.append(p)

    # Deterministic order: sorted by lowercased repo_id
    peers.sort(key=lambda p: p["repo_id"].lower())
    return peers


def _discover_fixtures(fixtures: FixturesLoader) -> list[dict]:
    peers: list[dict] = []
    seen: set[str] = set()
    for node_name in fixtures.list_nodes():
        descriptor_raw = fixtures.load_json(node_name, "agent-federation.json")
        if not descriptor_raw or not isinstance(descriptor_raw, dict):
            continue
        if descriptor_raw.get("kind") != "agent_federation_descriptor":
            continue
        repo_id = str(descriptor_raw.get("repo_id", node_name))
        if repo_id in seen:
            continue
        seen.add(repo_id)
        peer_raw = fixtures.load_json(node_name, "peer.json")
        peer = peer_raw if isinstance(peer_raw, dict) else None
        peers.append({
            "node_name": node_name, "repo_id": repo_id,
            "descriptor": descriptor_raw, "peer": peer, "base_url": "",
            "discovery_method": "fixtures",
            "default_branch": "main",
        })
    return peers


# ── Phase 2: Communication ──────────────────────────────────────────


def _read_outbox_network(base_url: str, outbox_path: str) -> list[dict] | None:
    url = f"{base_url}/{outbox_path}"
    data = _fetch_json(url)
    if isinstance(data, list):
        return data
    return None


def _read_outbox_fixtures(fixtures: FixturesLoader, node_name: str) -> list[dict] | None:
    data = fixtures.load_json(node_name, "nadi_outbox.json")
    if isinstance(data, list):
        return data
    return None


def _count_flows(envelopes: list[dict]) -> tuple[int, dict[str, int], set[str]]:
    depth = len(envelopes)
    targets: dict[str, int] = {}
    sources: set[str] = set()
    for env in envelopes:
        if not isinstance(env, dict):
            continue
        # Real federation envelopes use "source"/"target" (agent-internet, steward).
        # agent-template nadi_send.py uses "source_city_id"/"target_city_id".
        # Accept both — the field name is the only difference; semantics are identical.
        target = str(
            env.get("target", "")
            or env.get("target_city_id", "")
        ).strip()
        source = str(
            env.get("source", "")
            or env.get("source_city_id", "")
        ).strip()
        if target:
            targets[target] = targets.get(target, 0) + 1
        if source:
            sources.add(source)
    return depth, targets, sources


# ── Phase 3: Authority ──────────────────────────────────────────────


def _check_authority_feed_network(base_url: str, repo_id: str) -> bool:
    # The authority feed is published on a dedicated "authority-feed" branch,
    # not in a directory called "authority-feed/" on main.
    # repo_id = "kimeisele/steward" → branch URL.
    url = f"https://raw.githubusercontent.com/{repo_id}/authority-feed/latest-authority-manifest.json"
    data = _fetch_json(url)
    return isinstance(data, dict) and data.get("kind") == "source_authority_feed_manifest"


def _check_authority_feed_fixtures(fixtures: FixturesLoader, node_name: str) -> bool:
    data = fixtures.load_json(node_name, "latest-authority-manifest.json")
    return isinstance(data, dict) and data.get("kind") == "source_authority_feed_manifest"


# ── Phase 4: Topology ───────────────────────────────────────────────


def _classify_role(descriptor: dict) -> str:
    caps = [c.lower() for c in descriptor.get("capabilities", [])]
    layer = str(descriptor.get("layer", "")).lower()
    if "nadi-relay" in caps:
        return "RELAY"
    if layer == "internet":
        return "PROTOCOL"
    if "governance" in caps:
        return "GOVERNANCE"
    if any(c.startswith("research") for c in caps):
        return "RESEARCH"
    if "code_analysis" in caps or "task_execution" in caps or "ci_automation" in caps:
        return "EXECUTION"
    if "federation-visualization" in caps:
        return "OBSERVER"
    if "test-target" in caps:
        return "TEMPLATE"
    if "authority-publishing" in caps:
        return "OUTPOST"
    if layer == "protocol":
        return "PROTOCOL"
    return "GENERIC"


def _determine_status(descriptor: dict, outbox_reachable: bool) -> str:
    declared = str(descriptor.get("status", "")).lower()
    if declared != "active":
        return "SLEEPING"
    if not outbox_reachable:
        return "UNREACHABLE"
    return "ACTIVE"


def _depth_bin(depth: int) -> int:
    if depth == 0:
        return 0
    if depth <= 3:
        return 1
    if depth <= 10:
        return 2
    if depth <= 50:
        return 3
    return 4


_ACTIVITY_GLYPHS = ["·", "░", "▒", "▓", "█"]
_UNREACHABLE_GLYPH = "─"


def _activity_glyph(depth: int, outbox_reachable: bool) -> str:
    if not outbox_reachable:
        return _UNREACHABLE_GLYPH
    return _ACTIVITY_GLYPHS[_depth_bin(depth)]


def _compute_topology(
    peers: list[dict],
    outbox_data: dict[str, tuple[int, dict[str, int], set[str]]],
    authority_data: dict[str, bool],
    prev_history: list[dict],
) -> dict:
    nodes: dict[str, dict] = {}
    all_flows: dict[str, int] = {}
    total_in_flight = 0

    for p in peers:
        node_name = p["node_name"]
        descriptor = p["peer"] if p["peer"] else p["descriptor"]
        outbox = outbox_data.get(node_name)
        outbox_reachable = outbox is not None
        depth, targets, sources = outbox if outbox_reachable else (0, {}, set())
        total_in_flight += depth

        # Merge capabilities from both surfaces: descriptor + peer
        desc_caps = [c.lower() for c in p["descriptor"].get("capabilities", [])]
        peer_caps = [c.lower() for c in p.get("peer", {}).get("capabilities", [])] if p["peer"] else []
        merged_caps = sorted(set(desc_caps + peer_caps))

        # Build a merged view for role classification
        merged_descriptor = dict(p["descriptor"])
        merged_descriptor["capabilities"] = merged_caps

        status = _determine_status(p["descriptor"], outbox_reachable)
        role = _classify_role(merged_descriptor)
        layer = str(p["descriptor"].get("layer", "node")).lower()
        has_feed = authority_data.get(node_name, False)

        for target, count in targets.items():
            key = f"{node_name}>{target}"
            all_flows[key] = all_flows.get(key, 0) + count

        nodes[node_name] = {
            "node_name": node_name,
            "repo_id": p["repo_id"],
            "status": status, "role": role, "layer": layer,
            "depth": depth,
            "depth_bin": _depth_bin(depth) if outbox_reachable else -1,
            "outbox_reachable": outbox_reachable,
            "has_authority_feed": has_feed,
            "flow_targets": targets,
            "flow_sources": list(sources),
            "capabilities": merged_caps,
        }

    # Communicating = outbox reachable AND queue depth > 0
    communicating = sum(
        1 for n in nodes.values()
        if n["outbox_reachable"] and n["depth"] > 0
    )

    now_ts = time.time()
    for n in nodes.values():
        if n["status"] == "UNREACHABLE" and prev_history:
            last_seen: float = 0.0
            for entry in prev_history:
                depths = entry.get("depth", {})
                if n["node_name"] in depths:
                    last_seen = max(last_seen, entry.get("ts_epoch", 0))
            if last_seen > 0 and (now_ts - last_seen) > 7 * 24 * 3600:
                n["status"] = "FROZEN"

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nodes": nodes,
        "flows": all_flows,
        "summary": {
            "total_nodes": len(nodes),
            "communicating": communicating,
            "in_flight": total_in_flight,
            "feeds": sum(1 for n in nodes.values() if n["has_authority_feed"]),
        },
    }


# ── Phase 5: Render ─────────────────────────────────────────────────

INNER = 70  # inner content width (box border chars not included)

# Box drawing constants — computed from INNER
TOP = "┌" + "─" * INNER + "┐"
SEP = "├" + "─" * INNER + "┤"
BOT = "└" + "─" * INNER + "┘"


def _dwidth(s: str) -> int:
    """Display width — all glyphs we use are width-1 in monospace."""
    return len(s)


def _pad(s: str) -> str:
    """Pad *s* to INNER width and wrap in box borders.
    *s* carries NO leading/trailing border — _pad adds them.
    """
    return "│" + s + " " * max(0, INNER - _dwidth(s)) + "│"


def _fit(name: str, width: int = 20) -> str:
    """Truncate *name* to *width* with ellipsis if needed."""
    if len(name) <= width:
        return name
    return name[: width - 1] + "…"


# ── Layer bands (data-driven) ──────────────────────────────────────

# Known layers get curated labels + explicit sort order.
# Unknown layers keep their own identity (never merged into "OTHER")
# and sort after known layers, alphabetically.
LAYER_META: dict[str, tuple[int, str]] = {
    "visibility": (0, "AKASHA · observation"),
    "internet":   (1, "INTERNET · relay/transport"),
    "protocol":   (2, "PROTOCOL · governance/authority"),
    "node":       (3, "NODE · execution/citizens"),
}


def _layer_order(layer: str) -> tuple[int, str]:
    lo = layer.lower()
    if lo in LAYER_META:
        return (LAYER_META[lo][0], lo)
    return (99, lo)  # unknown: after known, stable by name


def _layer_label(layer: str) -> str:
    lo = layer.lower()
    return LAYER_META[lo][1] if lo in LAYER_META else layer.upper()


# ── Sparklines / trends ────────────────────────────────────────────


def _sparkline(values: list[int], width: int = 5) -> str:
    if not values:
        return "─" * width
    if len(values) < 2:
        return "·" * width
    bars = "▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    if mx == mn:
        return "▁" * min(width, len(values))
    result: list[str] = []
    for v in values[-width:]:
        idx = min(len(bars) - 1, max(0, round((v - mn) / (mx - mn) * (len(bars) - 1))))
        result.append(bars[idx])
    while len(result) < width:
        result.insert(0, " ")
    return "".join(result)


def _trend_arrow(depth_values: list[int]) -> str:
    if len(depth_values) < 2:
        return " "
    recent = depth_values[-3:] if len(depth_values) >= 3 else depth_values[-2:]
    if recent[-1] > recent[0]:
        return "↑"
    elif recent[-1] < recent[0]:
        return "↓"
    return " "


def _render_terrain(topology: dict, history: list[dict]) -> str:
    nodes = topology["nodes"]
    if not nodes:
        return _pad("  (no nodes discovered)") + "\n"

    depth_history: dict[str, list[int]] = {}
    for entry in history:
        for name, d in entry.get("depth", {}).items():
            depth_history.setdefault(name, []).append(d)

    # Data-driven: group by actual layer string, ordered by _layer_order
    bands: dict[str, list[dict]] = {}
    for n in nodes.values():
        bands.setdefault(n["layer"], []).append(n)

    sorted_layers = sorted(bands.keys(), key=_layer_order)
    for layer in sorted_layers:
        bands[layer].sort(key=lambda n: (0 if n["outbox_reachable"] else 1, -n["depth"]))

    lines: list[str] = []
    for layer in sorted_layers:
        label = _layer_label(layer)
        lines.append(_pad("  " + label))
        for n in bands[layer]:
            glyph = _activity_glyph(n["depth"], n["outbox_reachable"])
            depth_vals = depth_history.get(n["node_name"], [])
            spark = _sparkline(depth_vals[-8:]) if depth_vals else "─" * 5
            trend = _trend_arrow(depth_vals) if depth_vals else " "
            depth_str = str(n["depth"]) if n["outbox_reachable"] else "—"
            name = _fit(n["node_name"], 22)
            flags: list[str] = []
            if n["has_authority_feed"]:
                flags.append("feed")
            if n["status"] == "SLEEPING":
                flags.append("sleeping")
            elif n["status"] == "UNREACHABLE":
                flags.append("unreachable")
            elif n["status"] == "FROZEN":
                flags.append("frozen")
            elif n["role"] == "TEMPLATE":
                flags.append("template")
            elif n["role"] == "OBSERVER":
                flags.append("observer")
            elif n["outbox_reachable"] and n["depth"] == 0:
                flags.append("silent")
            flag_str = " · ".join(flags) if flags else ""
            if n["outbox_reachable"]:
                row = f"    {glyph} {name:<22} {spark} {depth_str:>5} {trend}  {flag_str}"
            else:
                row = f"    {glyph} {name:<22} {spark} {depth_str:>5}    {flag_str}"
            # Belt-and-suspenders: truncate if still too long
            if _dwidth(row) > INNER:
                row = row[: INNER - 1] + "…"
            lines.append(_pad(row))
        # Band separator
        lines.append(_pad("─" * (INNER - 2)))

    return "\n".join(lines)


def _render_flows(topology: dict) -> str:
    flows = topology.get("flows", {})
    if not flows:
        return _pad("  (no flow data — envelopes may lack target_city_id)") + "\n"

    ranked = sorted(flows.items(), key=lambda x: -x[1])
    top_n = ranked[:12]
    silent = {
        n["node_name"] for n in topology["nodes"].values()
        if n["outbox_reachable"] and n["depth"] == 0
    }
    silent.update(
        n["node_name"] for n in topology["nodes"].values()
        if not n["outbox_reachable"]
    )
    speaking = {f.split(">")[0] for f, _ in ranked}
    silent = silent - speaking

    lines: list[str] = []
    lines.append(_pad("  FEDERATION FLOWS · directed, from live NADI envelopes"))

    if not top_n:
        lines.append(_pad("    (all nodes silent this cycle)"))
    else:
        max_count = top_n[0][1]
        for flow_key, count in top_n:
            source, target = flow_key.split(">", 1)
            src = _fit(source, 20)
            tgt = _fit(target, 20)
            bar_len = max(1, round(count / max_count * 4))
            bar = "█" * bar_len
            row = f"    {src:<20} ──▶ {tgt:<20} {count:>4}  {bar}"
            lines.append(_pad(row))

    if silent:
        silent_str = ", ".join(sorted(silent))
        row = f"    silent: {silent_str}"
        if _dwidth(row) > INNER:
            row = row[: INNER - 3] + "…"
        lines.append(_pad(row))

    return "\n".join(lines)


def _render_pulse(topology: dict, history: list[dict]) -> str:
    summary = topology["summary"]
    total = summary["total_nodes"]
    communicating = summary["communicating"]
    in_flight = summary["in_flight"]
    feeds = summary["feeds"]

    active_hist: list[int] = []
    flight_hist: list[int] = []
    for entry in history[-8:]:
        active_hist.append(entry.get("active", 0))
        flight_hist.append(entry.get("in_flight", 0))

    active_spark = _sparkline(active_hist) if len(active_hist) >= 2 else "·" * 5
    flight_spark = _sparkline(flight_hist) if len(flight_hist) >= 2 else "·" * 5
    flight_trend = _trend_arrow(flight_hist) if len(flight_hist) >= 2 else " "

    delta_str = ""
    if len(flight_hist) >= 2 and flight_hist[-2] > 0:
        delta = flight_hist[-1] - flight_hist[-2]
        delta_str = f"  {delta:+d}"

    nodes = topology["nodes"]
    busiest = max(nodes.values(), key=lambda n: n["depth"]) if nodes else None
    quietest = min(nodes.values(), key=lambda n: n["depth"]) if nodes else None

    lines: list[str] = []
    bar = "▁"
    lines.append(_pad("  FEDERATION PULSE"))
    lines.append(_pad(f"    nodes       {total:>3}   {bar * 5}  steady"))
    lines.append(_pad(f"    comming     {communicating:>3}   {active_spark}  {_trend_arrow(active_hist)}"))
    lines.append(_pad(f"    in flight   {in_flight:>3}   {flight_spark}  {flight_trend}{delta_str}"))
    lines.append(_pad(f"    feeds       {feeds}/{total}   {bar * 5}  steady"))

    if busiest:
        name = _fit(busiest["node_name"], 20)
        lines.append(_pad(f"    busiest     {name} · {busiest['depth']} pending"))
    if quietest:
        name = _fit(quietest["node_name"], 20)
        lines.append(_pad(f"    quietest    {name} · {quietest['depth']} msgs"))

    if busiest and history:
        busiest_depths: list[int] = []
        for entry in history:
            d = entry.get("depth", {})
            if busiest["node_name"] in d:
                busiest_depths.append(d[busiest["node_name"]])
        if len(busiest_depths) >= 6 and all(
            busiest_depths[i] <= busiest_depths[i + 1]
            for i in range(len(busiest_depths) - 1)
        ):
            warn_name = _fit(busiest["node_name"], 16)
            lines.append(_pad(f"    ⚠ {warn_name} backlog rising {len(busiest_depths)} cycles"))

    return "\n".join(lines)


def _render_full(topology: dict, history: list[dict], cycle: int) -> str:
    ts = topology["generated_at"]
    summary = topology["summary"]
    terrain = _render_terrain(topology, history)
    flows = _render_flows(topology)
    pulse = _render_pulse(topology, history)

    header1 = f"  AGENT FEDERATION · TERRAIN           cycle #{cycle} · {ts}"
    header2 = "  elevation = live NADI activity                · ░ ▒ ▓ █  low → high"
    header3 = f"  {summary['total_nodes']} nodes · {summary['communicating']} communicating · {summary['in_flight']} in flight · {summary['feeds']}/{summary['total_nodes']} feeds"

    return f"""\
{TOP}
{_pad(header1)}
{_pad(header2)}
{_pad(header3)}
{SEP}
{terrain}
{SEP}
{flows}
{SEP}
{pulse}
{SEP}
{_render_terra_map(topology, history)}
{BOT}"""


# ── Terra Map (spatial panel) ───────────────────────────────────────

# Canvas dimensions
_CANVAS_W = 54
_CANVAS_H = 16

# Territory → visual label (kept short — territory header)
_BIOME_LABELS: dict[str, str] = {
    "RELAY": "RELAY",
    "GOVERNANCE": "GOVERN",
    "RESEARCH": "RESEARCH",
    "EXECUTION": "EXEC",
    "OUTPOST": "OUTPOST",
    "OBSERVER": "ORBIT",
    "PROTOCOL": "PROTOCOL",
    "TEMPLATE": "SANDBOX",
    "GENERIC": "OPEN",
}

# Territory border glyph — placed between territories only, never as fill
_BORDER_GLYPH = "·"


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    """1 - Jaccard similarity. 0 = identical, 1 = completely different."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return 1.0 - (intersection / union)


def _render_terra_map(topology: dict, _history: list[dict]) -> str:
    """Render the spatial Terra Map panel: structure = geography, activity = weather."""
    nodes = topology["nodes"]
    if not nodes:
        return _pad("  (no nodes — map empty)")

    node_list = sorted(nodes.values(), key=lambda n: n["node_name"])

    # ── 1. Territories from role ─────────────────────────────────────
    territories: dict[str, list[dict]] = {}
    for n in node_list:
        territories.setdefault(n["role"], []).append(n)

    _ROLE_ORDER = {r: i for i, r in enumerate(_BIOME_LABELS.keys())}
    sorted_roles = sorted(
        territories.keys(),
        key=lambda r: (_ROLE_ORDER.get(r, 99), r),
    )

    # ── 2. Within each territory: order by capability similarity ────
    # Greedy chain: cumulative Jaccard distance → real spatial separation
    cap_sets: dict[str, set[str]] = {}
    for n in node_list:
        cap_sets[n["node_name"]] = {c.lower() for c in n.get("capabilities", [])}

    # Per-territory: ordered list + cumulative distances
    territory_layout: dict[str, list[tuple[dict, float]]] = {}
    for role in sorted_roles:
        t_nodes = list(territories[role])
        if len(t_nodes) <= 1:
            territory_layout[role] = [(t_nodes[0], 0.0)] if t_nodes else []
            continue
        # Greedy chain
        ordered = [t_nodes[0]]
        remaining = t_nodes[1:]
        while remaining:
            last = ordered[-1]
            remaining.sort(
                key=lambda n: _jaccard_distance(
                    cap_sets[last["node_name"]], cap_sets[n["node_name"]]
                )
            )
            ordered.append(remaining.pop(0))
        # Cumulative distances along the chain
        pairs: list[tuple[dict, float]] = [(ordered[0], 0.0)]
        cum = 0.0
        for i in range(1, len(ordered)):
            d = _jaccard_distance(
                cap_sets[ordered[i - 1]["node_name"]],
                cap_sets[ordered[i]["node_name"]],
            )
            cum += max(d, 0.01)  # floor so identical-cap nodes still separate
            pairs.append((ordered[i], cum))
        territory_layout[role] = pairs

    # ── 3. Assign Y bands to territories ─────────────────────────────
    n_territories = len(sorted_roles)
    # Fit within canvas: each territory gets at least 1 row, with a gap between
    total_slots = _CANVAS_H - 1  # top margin
    gap_rows = n_territories - 1
    rows_per = max(1, (total_slots - gap_rows) // n_territories)
    band_rows: dict[str, tuple[int, int]] = {}
    y = 1
    for role in sorted_roles:
        band_rows[role] = (y, min(y + rows_per - 1, _CANVAS_H - 2))
        y = min(y + rows_per + 1, _CANVAS_H - 1)  # +1 for separator

    # ── 4. Place nodes on canvas ─────────────────────────────────────
    canvas = [[" " for _ in range(_CANVAS_W)] for _ in range(_CANVAS_H)]

    # Territory border rows (thin coastline between territories)
    for idx in range(len(sorted_roles) - 1):
        role = sorted_roles[idx]
        _, y1 = band_rows[role]
        sep_y = y1 + 1
        if sep_y < _CANVAS_H:
            for x in range(0, _CANVAS_W, 3):
                canvas[sep_y][x] = _BORDER_GLYPH

    placements: list[tuple[int, int, dict, int]] = []

    for role in sorted_roles:
        layout = territory_layout.get(role, [])
        if not layout:
            continue
        y0, y1 = band_rows[role]
        mid_y = (y0 + y1) // 2
        n = len(layout)

        # Scale cumulative distances to canvas width
        max_dist = layout[-1][1] if layout else 0.0
        if max_dist <= 0.0:
            # Single node or all identical → center in territory
            margin = 2
            usable = _CANVAS_W - 2 * margin
            if n == 1:
                x = margin + usable // 2
                placements.append((mid_y, x, layout[0][0], len(placements) + 1))
            else:
                step = usable / max(n - 1, 1)
                for i, (node, _) in enumerate(layout):
                    x = margin + int(step * i)
                    placements.append((mid_y, x, node, len(placements) + 1))
        else:
            margin = 2
            usable = _CANVAS_W - 2 * margin
            for node, cum_dist in layout:
                frac = cum_dist / max_dist
                x = margin + int(frac * usable)
                # Deterministic vertical jitter: hash node name for offset
                seed = sum(ord(c) for c in node["node_name"])
                jitter_y = mid_y + (seed % 3) - 1  # -1, 0, or +1
                jitter_y = max(y0, min(y1, jitter_y))
                # If occupied, use mid_y
                if canvas[jitter_y][x] != " ":
                    jitter_y = mid_y
                # Final clamp
                jitter_y = max(y0, min(y1, jitter_y))
                placements.append((jitter_y, x, node, len(placements) + 1))

    # ── 5. Apply weather glyphs ──────────────────────────────────────
    for y, x, node, _ in placements:
        glyph = _activity_glyph(node["depth"], node["outbox_reachable"])
        canvas[y][x] = glyph

    # ── 6. Build output ──────────────────────────────────────────────
    lines: list[str] = []
    lines.append(_pad("  TERRA MAP · structure = geography · activity = weather"))

    for role in sorted_roles:
        y0, y1 = band_rows[role]
        label = _BIOME_LABELS.get(role, role.upper())
        lines.append(_pad(f"  ── {label}"))
        for y in range(y0, y1 + 1):
            lines.append(_pad("  " + "".join(canvas[y])))

    lines.append(_pad("  "))

    # ── 7. Numbered legend ───────────────────────────────────────────
    legend_parts: list[str] = []
    for _, _, node, num in sorted(placements, key=lambda p: p[3]):
        glyph = _activity_glyph(node["depth"], node["outbox_reachable"])
        name = _fit(node["node_name"], 16)
        flag = ""
        if node["status"] == "SLEEPING":
            flag = " zzz"
        elif node["status"] == "UNREACHABLE":
            flag = " !"
        legend_parts.append(f"  {glyph} {num:>2} {name}{flag}")

    items_per_row = 3
    for i in range(0, len(legend_parts), items_per_row):
        row_parts = legend_parts[i : i + items_per_row]
        row = "  ".join(row_parts)
        lines.append(_pad(row))

    return "\n".join(lines)


# ── README injection ────────────────────────────────────────────────


def _inject_into_readme(map_text: str) -> bool:
    if not README_PATH.exists():
        return False
    content = README_PATH.read_text()
    start_idx = content.find(MARKER_START)
    end_idx = content.find(MARKER_END)
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return False
    before = content[: start_idx + len(MARKER_START)]
    after = content[end_idx:]
    # Wrap in a fenced code block so GitHub renders the box-drawing art in a
    # monospace font — without the fence, markdown reflows it into garbage.
    fenced = "```\n" + map_text + "\n```"
    new_content = before + "\n\n" + fenced + "\n\n" + after
    if new_content == content:
        return False
    README_PATH.write_text(new_content)
    return True


# ── History ──────────────────────────────────────────────────────────


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    entries: list[dict] = []
    for line in HISTORY_PATH.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _save_history(entries: list[dict]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = entries[-HISTORY_CAP:]
    HISTORY_PATH.write_text(
        "\n".join(json.dumps(e, sort_keys=True, separators=(",", ":")) for e in trimmed) + "\n"
    )


def _topology_content_hash(topology: dict) -> str:
    payload = {k: v for k, v in topology.items() if k != "generated_at"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _last_content_hash() -> str | None:
    if not LAST_HASH.exists():
        return None
    return LAST_HASH.read_text().strip() or None


def _save_content_hash(h: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_HASH.write_text(h + "\n")


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Render federation terrain map")
    parser.add_argument(
        "--fixtures", type=Path, default=None,
        help="Load peer surfaces from a local fixtures directory (offline mode)",
    )
    parser.add_argument(
        "--discover-dry-run", action="store_true",
        help="Only run discovery and print peers, then exit (no render)",
    )
    args = parser.parse_args()

    fixtures: FixturesLoader | None = None
    if args.fixtures:
        fixtures = FixturesLoader(args.fixtures)

    # ── Phase 1: Discover ────────────────────────────────────────────
    seeds_raw = json.loads(SEEDS_PATH.read_text())
    seed_urls: list[str] = seeds_raw.get("descriptor_urls", [])

    if fixtures:
        peers = _discover_fixtures(fixtures)
    else:
        peers = _discover_live(seed_urls)

    if not peers:
        print("No peers discovered.", file=sys.stderr)
        return 1

    # Dry-run mode: print discovered peers and exit
    if args.discover_dry_run:
        for p in peers:
            method = p.get("discovery_method", "fixtures" if fixtures else "seed")
            print(f"  {p['repo_id']:<40} ({method})")
        print(f"\nTotal: {len(peers)} peer(s)")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    peers_json = [
        {
            "node_name": p["node_name"], "repo_id": p["repo_id"],
            "status": p["descriptor"].get("status"),
            "layer": p["descriptor"].get("layer"),
            "capabilities": p["descriptor"].get("capabilities", []),
            "city_id": p["peer"].get("identity", {}).get("city_id", "") if p["peer"] else "",
            "transport": p["peer"].get("endpoint", {}).get("transport", "") if p["peer"] else "",
            "discovery_method": p.get("discovery_method", "fixtures" if fixtures else "seed"),
        }
        for p in peers
    ]
    PEERS_PATH.write_text(json.dumps(peers_json, indent=2, sort_keys=True) + "\n")

    # ── Phase 2: Communication ───────────────────────────────────────
    outbox_data: dict[str, tuple[int, dict[str, int], set[str]]] = {}
    for p in peers:
        node_name = p["node_name"]
        if fixtures:
            envelopes = _read_outbox_fixtures(fixtures, node_name)
        else:
            outbox_path = (
                p["peer"].get("nadi", {}).get("outbox", "data/federation/nadi_outbox.json")
                if p["peer"] else "data/federation/nadi_outbox.json"
            )
            envelopes = _read_outbox_network(p["base_url"], outbox_path)
        if envelopes is not None:
            depth, targets, sources = _count_flows(envelopes)
            outbox_data[node_name] = (depth, targets, sources)

    # ── Phase 3: Authority ───────────────────────────────────────────
    authority_data: dict[str, bool] = {}
    for p in peers:
        node_name = p["node_name"]
        authority_data[node_name] = (
            _check_authority_feed_fixtures(fixtures, node_name)
            if fixtures
            else _check_authority_feed_network(p["base_url"], p["repo_id"])
        )

    # ── Phase 4: Topology ────────────────────────────────────────────
    prev_history = _load_history()
    cycle = (prev_history[-1]["cycle"] + 1) if prev_history else 1

    topology = _compute_topology(peers, outbox_data, authority_data, prev_history)
    TOPOLOGY_PATH.write_text(json.dumps(topology, indent=2, sort_keys=True) + "\n")

    history_entry: dict[str, Any] = {
        "ts": topology["generated_at"],
        "ts_epoch": time.time(),
        "cycle": cycle,
        "depth": {n["node_name"]: n["depth"] for n in topology["nodes"].values()},
        "active": topology["summary"]["communicating"],
        "in_flight": topology["summary"]["in_flight"],
        "flows": topology["flows"],
    }
    prev_history.append(history_entry)
    _save_history(prev_history)

    # ── Phase 5: Render ──────────────────────────────────────────────
    map_text = _render_full(topology, prev_history, cycle)
    changed = _inject_into_readme(map_text)

    # Commit gating: compare content excluding the volatile header
    # (cycle number and timestamp change every run).
    # Use topology content hash — the source of truth for meaningful changes.
    content_hash = _topology_content_hash(topology)
    last_hash = _last_content_hash()
    hash_changed = (last_hash is None) or (content_hash != last_hash)

    # Always persist hash for next comparison
    _save_content_hash(content_hash)

    # Signal the workflow: commit on hash change OR hourly heartbeat
    needs_commit = hash_changed or (cycle % 4 == 0)  # ~hourly heartbeat

    if needs_commit and changed:
        (DATA_DIR / ".needs_commit").write_text("1\n")
    else:
        nf = DATA_DIR / ".needs_commit"
        if nf.exists():
            nf.unlink()

    communicating = topology["summary"]["communicating"]
    print(f"Cycle #{cycle} · {topology['summary']['total_nodes']} nodes · "
          f"{communicating} communicating · "
          f"{topology['summary']['in_flight']} in flight")
    print(f"Content hash: {content_hash[:12]}… "
          f"({'CHANGED' if hash_changed else 'same'})")
    if changed:
        print("README_UPDATED")
    if needs_commit:
        print("NEEDS_COMMIT")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
