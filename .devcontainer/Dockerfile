# Reproducible development / deployment environment for chainflip-eth-contracts.
#
# The goal of this image is DETERMINISTIC contract bytecode and CREATE/CREATE2
# addresses across every developer machine (incl. Mac M4 / arm64) and CI. solc
# embeds a CBOR metadata hash at the end of each contract's bytecode; that hash
# includes solc's `settings.remappings`, and brownie resolves the OpenZeppelin
# remapping to an ABSOLUTE path under the brownie data folder ($HOME/.brownie).
# So the value of $HOME leaks into every contract's bytecode and thus into the
# CREATE2 deposit addresses. This image neutralises the per-machine variation by
# pinning:
#   - platform  -> linux/amd64 (matches x64 CI/production; emulated on M4)
#   - the repo  -> a FIXED path (/opt/chainflip-eth-contracts)
#   - HOME      -> /home/ubuntu  <-- MUST match the CI/production build host.
#       The canonical bytecode + the addresses hardcoded in tests/shared_tests.py
#       were produced on self-hosted ephemeral runners running as the `ubuntu`
#       user, i.e. brownie data folder /home/ubuntu/.brownie. Verified: this HOME
#       reproduces Deposit create2 addr 0x311373270d730749FF22fd3c1F9836AA803Be47a.
#   - solc      -> 0.8.20, OpenZeppelin -> 4.8.3, eth-brownie -> 1.18.2 (via lockfiles)
#
# Do NOT change the WORKDIR / HOME below without re-running `make verify-bytecode`
# and updating the hardcoded addresses in tests/shared_tests.py — they are part of
# the bytecode determinism contract.
#
# Build context is the REPO ROOT (see .devcontainer/docker-compose.yml), so COPY
# paths are repo-root-relative (e.g. pyproject.toml, .devcontainer/install_solc.py).
FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME=/home/ubuntu \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME=/opt/poetry

# Ubuntu 24.04 ships an `ubuntu` user (uid 1000) with home /home/ubuntu; ensure
# the dir exists. We run as root but with HOME=/home/ubuntu so Path.home() (and
# hence brownie's data folder) resolves to /home/ubuntu — see header.
RUN mkdir -p /home/ubuntu

# --- System deps + Python 3.9 (deadsnakes; Ubuntu 24.04 ships 3.12 which is out
#     of the pyproject range >=3.7.3,<3.11) -------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common ca-certificates curl git gnupg \
        build-essential jq zip \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.9 python3.9-venv python3.9-dev python3.9-distutils \
    && rm -rf /var/lib/apt/lists/*

# --- Node 18 (matches the test/release workflows) + global yarn + ganache-cli --
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install --global yarn ganache-cli \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && yarn --version && ganache-cli --version

# Fixed canonical project path — part of the determinism contract (see header).
WORKDIR /opt/chainflip-eth-contracts

# --- Poetry 2.2.1 (pinned) -----------------------------------------------------
ENV POETRY_VERSION=2.2.1
RUN curl -sSL https://install.python-poetry.org | python3.9 - \
    && ln -sf "${POETRY_HOME}/bin/poetry" /usr/local/bin/poetry \
    && poetry --version

# The venv poetry creates is symlinked to a stable path (/opt/venv) that lives
# OUTSIDE the runtime bind-mount, so `brownie`/`pytest` stay on PATH at runtime
# without needing to invoke poetry.
ENV PATH="/opt/venv/bin:${POETRY_HOME}/bin:${PATH}"

# --- Python deps from the committed lockfile (NO relock) -----------------------
COPY pyproject.toml poetry.lock ./
RUN poetry env use python3.9 \
    && poetry install --no-root \
    && ln -sfn "$(poetry env info --path)" /opt/venv \
    && brownie --version

# --- JS deps (provides @openzeppelin/contracts@4.8.3 under node_modules, used by
#     solc/hardhat/solidity-docgen/lint) ----------------------------------------
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# --- Pre-warm solc 0.8.20 into ~/.solcx + install OpenZeppelin for the brownie
#     package manager (~/.brownie), so the image compiles offline & deterministically.
#
#     py-solc-x 1.1.1 (pinned by eth-brownie) would download solc from the now-DEAD
#     host solc-bin.ethereum.org, so instead we drop the official static linux build
#     straight from GitHub releases into ~/.solcx as `solc-v0.8.20` (the filename
#     py-solc-x/brownie look up). solc is placed FIRST so the subsequent
#     `brownie pm install` compile step has a compiler available.
RUN set -e; \
    mkdir -p "$HOME/.solcx"; \
    curl -fL --retry 5 --retry-delay 3 \
        https://github.com/ethereum/solidity/releases/download/v0.8.20/solc-static-linux \
        -o "$HOME/.solcx/solc-v0.8.20"; \
    chmod +x "$HOME/.solcx/solc-v0.8.20"; \
    python3.9 -c "import solcx; vs=[str(v) for v in solcx.get_installed_solc_versions()]; assert '0.8.20' in vs, vs; print('solc:', vs)"; \
    n=0; until brownie pm install OpenZeppelin/openzeppelin-contracts@4.8.3; do \
        n=$((n+1)); [ "$n" -ge 5 ] && echo "brownie pm install failed after $n attempts" && exit 1; \
        echo "brownie pm install retry $n..."; sleep 5; \
    done

CMD ["bash"]
