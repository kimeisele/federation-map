"""Generate large fixture sets to stress-test federation-map scaling.

Usage:
    python tests/make_big_fixtures.py [output_dir] [node_count]

Output is a fixtures directory loadable by:
    python scripts/render_topology.py --fixtures <output_dir>
"""
import json
import os
import random
import sys


def build(base: str = "/tmp/bigfix", n: int = 24, seed: int = 7) -> str:
    random.seed(seed)
    os.makedirs(base, exist_ok=True)

    layers = ["internet", "protocol", "node", "node", "node",
              "visibility", "quantum", "mesh"]
    caps_options = [
        ["nadi-relay"], ["governance"], ["research_synthesis"],
        ["code_analysis"], ["federation-visualization"], ["authority-publishing"], []
    ]
    status_options = ["active", "active", "active", "sleeping"]
    depths = [0, 0, 1, 3, 8, 25, 60, 140]
    name_prefixes = [
        "nova", "flux", "echo", "kite", "sol", "vega", "oreo", "zephyr",
    ]

    names: list[str] = []
    for i in range(n):
        if i == 5:
            # One deliberately long name to exercise truncation
            names.append("steward-federation-observer-relay-node")
        else:
            prefix = random.choice(name_prefixes)
            names.append(f"agent-{prefix}-{i}")

    for i, name in enumerate(names):
        d = os.path.join(base, name)
        os.makedirs(d, exist_ok=True)

        caps = random.choice(caps_options)
        status = random.choice(status_options)
        layer = layers[i % len(layers)]

        descriptor = {
            "kind": "agent_federation_descriptor",
            "version": 1,
            "repo_id": f"kimeisele/{name}",
            "display_name": name.replace("-", " ").title(),
            "status": status,
            "layer": layer,
            "capabilities": caps,
            "endpoints": {"federation_descriptor": ".well-known/agent-federation.json"},
        }
        with open(os.path.join(d, "agent-federation.json"), "w") as f:
            json.dump(descriptor, f, indent=2, sort_keys=True)

        peer = {
            "identity": {"city_id": name, "repo": f"kimeisele/{name}"},
            "endpoint": {"transport": "filesystem"},
            "nadi": {
                "outbox": "data/federation/nadi_outbox.json",
                "inbox": "data/federation/nadi_inbox.json",
            },
            "capabilities": caps,
        }
        with open(os.path.join(d, "peer.json"), "w") as f:
            json.dump(peer, f, indent=2, sort_keys=True)

        depth = random.choice(depths)
        envelopes = []
        for _ in range(depth):
            envelopes.append({
                "envelope_id": f"e{random.randint(0, 9999)}",
                "source_city_id": name,
                "target_city_id": random.choice(names),
                "operation": "heartbeat",
                "nadi_type": "filesystem",
                "payload": {},
                "priority": 5,
                "ttl_ms": 300000,
            })
        with open(os.path.join(d, "nadi_outbox.json"), "w") as f:
            json.dump(envelopes, f, indent=2, sort_keys=True)

    # Also write a seed list so the renderer can discover these
    seeds = {
        "descriptor_urls": [
            f"https://raw.githubusercontent.com/kimeisele/{name}/main/.well-known/agent-federation.json"
            for name in names
        ]
    }
    # Don't overwrite real seed list — just note this in a README
    with open(os.path.join(base, "_seed_list.json"), "w") as f:
        json.dump(seeds, f, indent=2)

    return base


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bigfix"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    print(build(out, n))
