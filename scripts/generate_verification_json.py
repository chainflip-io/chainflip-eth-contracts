import json
import os
import sys

import brownie

DEPLOYMENTS_MAP = os.path.join("build", "deployments", "map.json")

# Usage: brownie run generate_verification_json main <chain_id> --network hardhat
# e.g.:  brownie run generate_verification_json main 97 --network hardhat


def main(chain_id=None):
    with open(DEPLOYMENTS_MAP) as f:
        deployments = json.load(f)

    if chain_id is None or str(chain_id) not in deployments:
        sys.exit(
            f"Unknown chain id: {chain_id}. "
            f"Chains in {DEPLOYMENTS_MAP}: {sorted(deployments.keys())}"
        )
    chain_id = str(chain_id)

    output_dir = os.path.join("build", f"verification-jsons-chain-{chain_id}")
    os.makedirs(output_dir, exist_ok=True)

    for name, addresses in deployments[chain_id].items():
        container = getattr(brownie, name, None)
        if container is None:
            print(f"WARNING: no contract container for {name}, skipping")
            continue

        info = container.get_verification_info()
        for address in addresses:
            path = os.path.join(output_dir, f"{name}-{address}-verify.json")
            with open(path, "w") as f:
                json.dump(info["standard_json_input"], f)
            print(f"Wrote {path} (chain {chain_id})")
