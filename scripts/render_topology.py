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
    """Load peer surfaces from a local fixtures directory.

    Directory layout:
        fixtures/
          agent-internet/
            agent-federation.json
            peer.json
            nadi_outbox.json
            latest-authority-manifest.json  (optional)
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def list_nodes(self) -> list[str]:
        """Return directory names that contain an agent-federation.json."""
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

    def load_text(self, node: str, filename: str) -> str | None:
        path = self._root / node / filename
        if not path.is_file():
            return None
        try:
            return path.read_text()
        except OSError:
            return None


# ── Phase 1: Discovery ──────────────────────────────────────────────


def _repo_id_to_node_name(repo_id: str) -> str:
    """Extract node name from repo_id like 'kimeisele/steward' -> 'steward'."""
    return repo_id.split("/")[-1]


def _node_base_url(repo_id: str) -> str:
    """Build the raw.githubusercontent.com base URL for a repo."""
    return f"https://raw.githubusercontent.com/{repo_id}/main"


def _discover_live(seed_urls: list[str]) -> list[dict]:
    """Discover peers via live raw.githubusercontent.com fetches."""
    peers: list[dict] = []
    seen: set[str] = set()

    for url in seed_urls:
        descriptor = _fetch_json(url)
        if not descriptor or not isinstance(descriptor, dict):
            continue
        if descriptor.get("kind") != "agent_federation_descriptor":
            continue

        repo_id = str(descriptor.get("repo_id", ""))
        if not repo_id:
            continue
        if repo_id in seen:
            continue
        seen.add(repo_id)

        node_name = _repo_id_to_node_name(repo_id)
        base = _node_base_url(repo_id)

        # Fetch peer.json
        peer = None
        peer_url = f"{base}/data/federation/peer.json"
        peer_data = _fetch_json(peer_url)
        if peer_data and isinstance(peer_data, dict):
            peer = peer_data

        peers.append({
            "node_name": node_name,
            "repo_id": repo_id,
            "descriptor": descriptor,
            "peer": peer,
            "base_url": base,
        })

    return peers


def _discover_fixtures(fixtures: FixturesLoader) -> list[dict]:
    """Discover peers from a fixtures directory."""
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
            "node_name": node_name,
            "repo_id": repo_id,
            "descriptor": descriptor_raw,
            "peer": peer,
            "base_url": "",
        })

    return peers


# ── Phase 2: Communication ──────────────────────────────────────────


def _read_outbox_network(base_url: str, outbox_path: str) -> list[dict] | None:
    """Fetch a peer's NADI outbox from the network."""
    url = f"{base_url}/{outbox_path}"
    data = _fetch_json(url)
    if isinstance(data, list):
        return data
    return None


def _read_outbox_fixtures(fixtures: FixturesLoader, node_name: str) -> list[dict] | None:
    """Read a peer's NADI outbox from fixtures."""
    try:
        data = fixtures.load_json(node_name, "nadi_outbox.json")
    except Exception:
        data = None
    if isinstance(data, list):
        return data
    return None


def _count_flows(envelopes: list[dict]) -> tuple[int, dict[str, int], set[str]]:
    """Count queue depth and per-target flows from envelopes.

    Returns: (depth, {target_city_id: count}, {source_city_ids})
    """
    depth = len(envelopes)
    targets: dict[str, int] = {}
    sources: set[str] = set()
    for env in envelopes:
        if not isinstance(env, dict):
            continue
        target = str(env.get("target_city_id", "")).strip()
        source = str(env.get("source_city_id", "")).strip()
        if target:
            targets[target] = targets.get(target, 0) + 1
        if source:
            sources.add(source)
    return depth, targets, sources


# ── Phase 3: Authority ──────────────────────────────────────────────


def _check_authority_feed_network(base_url: str) -> bool:
    """Check if a peer publishes an authority feed."""
    url = f"{base_url}/authority-feed/latest-authority-manifest.json"
    data = _fetch_json(url)
    if isinstance(data, dict) and data.get("kind") == "source_authority_feed_manifest":
        return True
    return False


def _check_authority_feed_fixtures(fixtures: FixturesLoader, node_name: str) -> bool:
    """Check if a node's fixtures contain an authority feed manifest."""
    data = fixtures.load_json(node_name, "latest-authority-manifest.json")
    if isinstance(data, dict) and data.get("kind") == "source_authority_feed_manifest":
        return True
    return False


# ── Phase 4: Topology ───────────────────────────────────────────────


def _classify_role(descriptor: dict) -> str:
    """Classify a node's role from its declared capabilities and layer."""
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
    """Determine node status from declared + observed state."""
    declared = str(descriptor.get("status", "")).lower()
    if declared != "active":
        return "SLEEPING"
    if not outbox_reachable:
        return "UNREACHABLE"
    return "ACTIVE"


def _depth_bin(depth: int) -> int:
    """Bin queue depth to a 0-4 activity level (log-ish).

    0=0, 1=1-3, 2=4-10, 3=11-50, 4=51+
    """
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
_UNKNOWN_GLYPH = "—"


def _activity_glyph(depth: int, outbox_reachable: bool) -> str:
    """Return the activity glyph for a given depth and reachability."""
    if not outbox_reachable:
        return _UNREACHABLE_GLYPH
    return _ACTIVITY_GLYPHS[_depth_bin(depth)]


def _compute_topology(
    peers: list[dict],
    outbox_data: dict[str, tuple[int, dict[str, int], set[str]]],
    authority_data: dict[str, bool],
    prev_history: list[dict],
) -> dict:
    """Compute the full topology from discovered peers and observations."""
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

        status = _determine_status(p["descriptor"], outbox_reachable)
        role = _classify_role(p["descriptor"])
        layer = str(p["descriptor"].get("layer", "node")).lower()
        has_feed = authority_data.get(node_name, False)

        # Accumulate flows
        for target, count in targets.items():
            key = f"{node_name}>{target}"
            all_flows[key] = all_flows.get(key, 0) + count

        nodes[node_name] = {
            "node_name": node_name,
            "repo_id": p["repo_id"],
            "status": status,
            "role": role,
            "layer": layer,
            "depth": depth,
            "depth_bin": _depth_bin(depth) if outbox_reachable else -1,
            "outbox_reachable": outbox_reachable,
            "has_authority_feed": has_feed,
            "flow_targets": targets,
            "flow_sources": list(sources),
            "capabilities": p["descriptor"].get("capabilities", []),
        }

    # Count actives
    active_count = sum(
        1 for n in nodes.values()
        if n["status"] == "ACTIVE" and n["outbox_reachable"]
    )

    # Check for frozen nodes (from history)
    now_ts = time.time()
    for n in nodes.values():
        if n["status"] == "UNREACHABLE" and prev_history:
            # Check if never seen in 7+ days across all history entries
            last_seen: float = 0.0
            for entry in prev_history:
                depths = entry.get("depth", {})
                if n["node_name"] in depths:
                    last_seen = max(last_seen, entry.get("ts_epoch", 0))
            if last_seen > 0 and (now_ts - last_seen) > 7 * 24 * 3600:
                n["status"] = "FROZEN"

    topology = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nodes": nodes,
        "flows": all_flows,
        "summary": {
            "total_nodes": len(nodes),
            "active": active_count,
            "in_flight": total_in_flight,
            "feeds": sum(1 for n in nodes.values() if n["has_authority_feed"]),
        },
    }
    return topology


# ── Phase 5: Render ─────────────────────────────────────────────────


def _sparkline(values: list[int], width: int = 5) -> str:
    """Render a sparkline from a list of integer values using Unicode blocks.

    Maps values to ▁▂▃▄▅▆▇█ using the range of the provided values.
    On a fresh repo (< 2 data points) returns a placeholder.
    """
    if not values:
        return "─" * width
    if len(values) < 2:
        return "·" * width  # warming up — not enough history

    bars = "▁▂▃▄▅▆▇█"
    mn = min(values)
    mx = max(values)
    if mx == mn:
        # All same — flat line
        return "▁" * min(width, len(values))

    result: list[str] = []
    for v in values[-width:]:
        idx = min(len(bars) - 1, max(0, round((v - mn) / (mx - mn) * (len(bars) - 1))))
        result.append(bars[idx])

    # Pad to requested width if we have fewer values
    while len(result) < width:
        result.insert(0, " ")
    return "".join(result)


def _trend_arrow(depth_values: list[int]) -> str:
    """Return a trend arrow based on last few depth values."""
    if len(depth_values) < 2:
        return " "
    recent = depth_values[-3:] if len(depth_values) >= 3 else depth_values[-2:]
    if recent[-1] > recent[0]:
        return "↑"
    elif recent[-1] < recent[0]:
        return "↓"
    return " "


def _layer_band(layer: str) -> int:
    """Map descriptor layer to a display band (higher = rendered first/top)."""
    band_order = {
        "visibility": 0,
        "internet": 1,
        "protocol": 2,
        "node": 3,
    }
    return band_order.get(layer.lower(), 4)


def _layer_label(layer: str) -> str:
    """Human-readable zone label for a layer."""
    labels = {
        "visibility": "AKASHA · observation",
        "internet": "INTERNET · relay/transport",
        "protocol": "PROTOCOL · governance/authority",
        "node": "NODE · execution/citizens",
    }
    return labels.get(layer.lower(), layer.upper())


def _render_terrain(topology: dict, history: list[dict]) -> str:
    """Render Panel A: Terrain map."""
    nodes = topology["nodes"]
    if not nodes:
        return "  (no nodes discovered)\n"

    # Build depth history per node from history.jsonl
    depth_history: dict[str, list[int]] = {}
    for entry in history:
        depths = entry.get("depth", {})
        for name, d in depths.items():
            if name not in depth_history:
                depth_history[name] = []
            depth_history[name].append(d)

    # Group by layer band, sort by activity desc within band
    bands: dict[int, list[dict]] = {}
    for n in nodes.values():
        band = _layer_band(n["layer"])
        bands.setdefault(band, [])
        bands[band].append(n)

    for band in bands:
        bands[band].sort(key=lambda n: (0 if n["outbox_reachable"] else 1, -n["depth"]))

    lines: list[str] = []
    separator = "─" * 70

    for band_idx in sorted(bands.keys()):
        label = _layer_label(list(bands[band_idx])[0]["layer"])
        lines.append(f"  {label}")
        for n in bands[band_idx]:
            glyph = _activity_glyph(n["depth"], n["outbox_reachable"])
            depth_vals = depth_history.get(n["node_name"], [])
            spark = _sparkline(depth_vals[-8:]) if depth_vals else ("─" * 5)
            trend = _trend_arrow(depth_vals) if depth_vals else " "
            depth_str = str(n["depth"]) if n["outbox_reachable"] else "—"
            flags: list[str] = []
            if n["has_authority_feed"]:
                flags.append("feed✓")
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
            flag_str = " · ".join(flags) if flags else ""
            if n["outbox_reachable"]:
                line = (
                    f"    {glyph} {n['node_name']:<24} {spark} {depth_str:>5} "
                    f" {trend}  {flag_str}"
                )
            else:
                line = (
                    f"    {glyph} {n['node_name']:<24} {spark} {depth_str:>5}"
                    f"    {flag_str}"
                )
            lines.append(line.rstrip())
        lines.append(f"  {separator}")

    return "\n".join(lines)


def _render_pulse(topology: dict, history: list[dict]) -> str:
    """Render Panel C: Federation Pulse."""
    summary = topology["summary"]
    total = summary["total_nodes"]
    active = summary["active"]
    in_flight = summary["in_flight"]
    feeds = summary["feeds"]

    # Build sparklines from history
    active_hist: list[int] = []
    flight_hist: list[int] = []
    for entry in history[-8:]:
        active_hist.append(entry.get("active", 0))
        flight_hist.append(entry.get("in_flight", 0))

    active_spark = _sparkline(active_hist) if active_hist else ("─" * 5)
    flight_spark = _sparkline(flight_hist) if flight_hist else ("─" * 5)

    # Trend for in_flight
    flight_trend = _trend_arrow(flight_hist) if len(flight_hist) >= 2 else " "
    pct = ""
    if len(flight_hist) >= 2 and flight_hist[-2] > 0:
        delta = flight_hist[-1] - flight_hist[-2]
        pct = f"  {delta:+d} vs. last cycle"

    # Find busiest and quietest nodes
    nodes = topology["nodes"]
    busiest = max(nodes.values(), key=lambda n: n["depth"]) if nodes else None
    quietest = min(nodes.values(), key=lambda n: n["depth"]) if nodes else None

    lines: list[str] = []
    lines.append("  FEDERATION PULSE")
    lines.append(f"    nodes       {total:>3}   ▁▁▁▁▁  steady")
    lines.append(f"    active      {active:>3}   {active_spark}  {_trend_arrow(active_hist)}")
    lines.append(f"    in flight   {in_flight:>3}   {flight_spark}  {flight_trend}{pct}")
    lines.append(f"    feeds       {feeds}/{total}   ▁▁▁▁▁  steady")

    if busiest:
        lines.append(
            f"    busiest     {busiest['node_name']} · "
            f"{busiest['depth']} pending"
        )
    if quietest:
        lines.append(
            f"    quietest    {quietest['node_name']} · "
            f"{quietest['depth']} msgs"
        )

    # Check for monotonic backlog growth (busiest rising N cycles)
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
            lines.append(
                f"    ⚠ {busiest['node_name']} backlog rising "
                f"{len(busiest_depths)} cycles — relay jam?"
            )

    return "\n".join(lines)


def _render_flows(topology: dict) -> str:
    """Render Panel B: Flows (directed edges from NADI envelopes)."""
    flows = topology.get("flows", {})
    if not flows:
        return "  (no flow data — envelopes may lack target_city_id)"

    # Sort by volume desc
    ranked = sorted(flows.items(), key=lambda x: -x[1])
    top_n = ranked[:12]
    silent = {
        n["node_name"]
        for n in topology["nodes"].values()
        if n["outbox_reachable"] and n["depth"] == 0
    }
    # Also include nodes that are unreachable
    silent.update(
        n["node_name"]
        for n in topology["nodes"].values()
        if not n["outbox_reachable"]
    )
    # Remove nodes that appear as sources in ranked flows
    speaking = {f.split(">")[0] for f, _ in ranked}
    silent = silent - speaking

    lines: list[str] = []
    lines.append("  FEDERATION FLOWS · directed, from live NADI envelopes")

    if not top_n:
        lines.append("    (all nodes silent this cycle)")
    else:
        max_count = top_n[0][1]
        for flow_key, count in top_n:
            source, target = flow_key.split(">", 1)
            bar_len = max(1, round(count / max_count * 4))
            bar = "█" * bar_len
            lines.append(f"    {source:<20} ──▶ {target:<20} {count:>4}  {bar}")

    if silent:
        lines.append(f"    silent: {', '.join(sorted(silent))}")

    return "\n".join(lines)


def _render_full(topology: dict, history: list[dict], cycle: int) -> str:
    """Render the complete map (all panels) into a Markdown string."""
    ts = topology["generated_at"]

    terrain = _render_terrain(topology, history)
    flows = _render_flows(topology)
    pulse = _render_pulse(topology, history)

    summary = topology["summary"]

    map_text = f"""\
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT FEDERATION · TERRAIN           cycle #{cycle} · {ts}   │
│  elevation = live NADI activity                · ░ ▒ ▓ █  low → high   │
│  {summary['total_nodes']} nodes · {summary['active']} active · {summary['in_flight']} in flight · {summary['feeds']}/{summary['total_nodes']} feeds                    │
├──────────────────────────────────────────────────────────────────────┤
{terrain}
├──────────────────────────────────────────────────────────────────────┤
{flows}
├──────────────────────────────────────────────────────────────────────┤
{pulse}
└──────────────────────────────────────────────────────────────────────┘"""

    return map_text


# ── README injection ────────────────────────────────────────────────


def _inject_into_readme(map_text: str) -> bool:
    """Replace the region between MARKER_START and MARKER_END in README.md.

    Returns True if the file changed.
    """
    if not README_PATH.exists():
        return False

    content = README_PATH.read_text()
    start_idx = content.find(MARKER_START)
    end_idx = content.find(MARKER_END)

    if start_idx == -1 or end_idx == -1:
        return False
    if start_idx >= end_idx:
        return False

    before = content[: start_idx + len(MARKER_START)]
    after = content[end_idx:]

    new_content = before + "\n\n" + map_text + "\n\n" + after
    if new_content == content:
        return False

    README_PATH.write_text(new_content)
    return True


# ── History ──────────────────────────────────────────────────────────


def _load_history() -> list[dict]:
    """Load the history.jsonl file as a list of dicts."""
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
    """Write history entries capped to HISTORY_CAP lines."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = entries[-HISTORY_CAP:]
    HISTORY_PATH.write_text(
        "\n".join(json.dumps(e, sort_keys=True, separators=(",", ":")) for e in trimmed) + "\n"
    )


def _topology_content_hash(topology: dict) -> str:
    """Hash of topology excluding generated_at."""
    payload = {k: v for k, v in topology.items() if k != "generated_at"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _last_content_hash() -> str | None:
    """Read the content hash stored after the last commit."""
    hash_path = DATA_DIR / ".last_topology_hash"
    if not hash_path.exists():
        return None
    return hash_path.read_text().strip() or None


def _save_content_hash(h: str) -> None:
    """Persist the content hash."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / ".last_topology_hash").write_text(h + "\n")


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Render federation terrain map")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Load peer surfaces from a local fixtures directory (offline mode)",
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

    # Write peers.json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    peers_json = [
        {
            "node_name": p["node_name"],
            "repo_id": p["repo_id"],
            "status": p["descriptor"].get("status"),
            "layer": p["descriptor"].get("layer"),
            "capabilities": p["descriptor"].get("capabilities", []),
            "city_id": p["peer"].get("identity", {}).get("city_id", "") if p["peer"] else "",
            "transport": p["peer"].get("endpoint", {}).get("transport", "") if p["peer"] else "",
        }
        for p in peers
    ]
    PEERS_PATH.write_text(json.dumps(peers_json, indent=2, sort_keys=True) + "\n")

    # ── Phase 2: Communication ───────────────────────────────────────
    outbox_data: dict[str, tuple[int, dict[str, int], set[str]]] = {}
    for p in peers:
        node_name = p["node_name"]
        if fixtures:
            outbox_path = "nadi_outbox.json"  # fixtures loader ignores the path
            envelopes = _read_outbox_fixtures(fixtures, node_name)
        else:
            outbox_path = (
                p["peer"].get("nadi", {}).get("outbox", "data/federation/nadi_outbox.json")
                if p["peer"]
                else "data/federation/nadi_outbox.json"
            )
            envelopes = _read_outbox_network(p["base_url"], outbox_path)

        if envelopes is not None:
            depth, targets, sources = _count_flows(envelopes)
            outbox_data[node_name] = (depth, targets, sources)

    # ── Phase 3: Authority ───────────────────────────────────────────
    authority_data: dict[str, bool] = {}
    for p in peers:
        node_name = p["node_name"]
        if fixtures:
            has_feed = _check_authority_feed_fixtures(fixtures, node_name)
        else:
            has_feed = _check_authority_feed_network(p["base_url"])
        authority_data[node_name] = has_feed

    # ── Phase 4: Topology ────────────────────────────────────────────
    prev_history = _load_history()
    cycle = len(prev_history) + 1

    topology = _compute_topology(peers, outbox_data, authority_data, prev_history)

    # Write topology.json
    TOPOLOGY_PATH.write_text(json.dumps(topology, indent=2, sort_keys=True) + "\n")

    # Append to history.jsonl
    history_entry: dict[str, Any] = {
        "ts": topology["generated_at"],
        "ts_epoch": time.time(),
        "cycle": cycle,
        "depth": {n["node_name"]: n["depth"] for n in topology["nodes"].values()},
        "active": topology["summary"]["active"],
        "in_flight": topology["summary"]["in_flight"],
        "flows": topology["flows"],
    }
    prev_history.append(history_entry)
    _save_history(prev_history)

    # ── Phase 5: Render ──────────────────────────────────────────────
    map_text = _render_full(topology, prev_history, cycle)
    changed = _inject_into_readme(map_text)

    # Commit gating
    content_hash = _topology_content_hash(topology)
    last_hash = _last_content_hash()
    _save_content_hash(content_hash)

    print(f"Cycle #{cycle} · {topology['summary']['total_nodes']} nodes · "
          f"{topology['summary']['active']} active · "
          f"{topology['summary']['in_flight']} in flight")
    if changed:
        print(f"README updated (content hash: {content_hash[:12]}…)")
    else:
        print(f"README unchanged (content hash: {content_hash[:12]}…)")
    if last_hash and content_hash != last_hash:
        print("HASH_CHANGED")
    else:
        print("HASH_SAME")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
