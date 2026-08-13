"""
Gas measurements for the state-chain fee constants of any secondary EVM chain
(chainflip-backend state-chain/chains/src/<chain>.rs, `pub mod fees`).

The state chain models a fetch/egress as:
    gas = BASE_COST_PER_BATCH + n * GAS_COST_PER_<item>
so a single-item batch cannot separate the intercept from the slope. Every measurement
below therefore runs at n = 1, 2, 3 in one `allBatch`: the slope is the per-item constant
and the intercept is the batch base cost. The analysis at the end of the module derives
every constant and prints it, including a coverage check of its own output.

Local (mock ERC20 from conftest's `token_minimal`, no real funds needed):

    brownie test tests/unit/vault/test_allBatchGasEstimate.py --network hardhat --stateful false

Live network, measuring against the chain's real token contract:

    export SEED="<mnemonic funded with the gas asset AND the token>"
    export TOKEN_ADDRESS=0x55d398326f99059fF775485246999027B3197955   # BSC-USDT
    brownie test tests/unit/vault/test_allBatchGasEstimate.py --network bsc-main --stateful false

PICK A LOW-VALUE TOKEN — a stablecoin. Amounts are 1% of one whole token (scaled by
decimals()) because token gas depends on decimals and on whether a balance slot crosses
zero, never on value. A run moves 0.45 of a token out of the account (45 transfers of 0.01)
and strands 0.12 of it in hash-derived addresses and CFTester contracts: cents in USDT,
hundreds of dollars in WBTC.

A live run deploys its own KeyManager, Vault, AddressChecker and one CFTester per CCM
case, and it moves real balances, so keep it to testnets unless you mean it. Set
RECIPIENT_SALT to a fresh value when re-running against a persistent chain: the
"new recipient" addresses are derived from it, so reusing it measures recipients an
earlier run already created, which is the cheaper case and understates the cost.
"""

import pytest
from os import environ
from brownie import Contract, chain, network
from consts import *
from utils import *
from shared_tests import *
from deploy import deploy_new_cfReceiver

# Salts the generated "new recipient" addresses, so a re-run against a persistent chain
# can get a set nothing has touched yet. Irrelevant on a throwaway node.
RECIPIENT_SALT = environ.get("RECIPIENT_SALT", "")

# Items per allBatch, and CCM message lengths in bytes: both the parameters the tests
# run at and the columns the analysis reads them back from.
COUNTS = [1, 2, 3]
CCM_LENGTHS = [0, 100, 1000]

# label -> {n: gas_used}, consumed by the analysis at the end of the module.
RESULTS = {}


# No fn_isolation: gas must be measured on a chain that is not rolled back between
# calls: a gas measurement is only meaningful against real, accumulated chain state.
@pytest.fixture(autouse=True)
def isolation():
    pass


def record(label, n, gas):
    # Measurements are only accumulated here; the analysis at the end of the module
    # reports every one of them, so nothing is printed per measurement.
    RESULTS.setdefault(label, {})[n] = gas


def fresh_addr(tag, n, i):
    # Deterministic address that has never been touched: zero balance, cold, and
    # (for tokens) a zero-value balance slot. The count `n` is part of the tag so that
    # parametrized runs of the same measurement never share an address — otherwise run
    # n=2 reuses the address run n=1 created and the marginal cost silently mixes fresh
    # and existing recipients.
    return web3.toChecksumAddress(web3.keccak(text=f"{RECIPIENT_SALT}-{tag}-{n}-{i}")[-20:].hex())


def is_local():
    return chain.id in [hardhat, eth_localnet, arb_localnet]


def confirm_live_run(config, token):
    """Confirm before touching a live chain: this run spends real gas and real tokens."""
    if is_local():
        return
    prompt = (
        f"\nLive run on {network.show_active()} (chainId {chain.id}) with "
        f"{token.symbol()} at {token.address}."
        f"\nIt deploys its own KeyManager/Vault/AddressChecker and moves 0.45"
        f" {token.symbol()} plus gas out of this account: 0.12 stranded (fresh"
        f" recipients, CFTesters), 0.33 retrievable (0.24 in the Vault it deploys, 0.09"
        f" in your own SEED accounts). Continue? [y/N]: "
    )
    # pytest redirects stdout AND stdin, so both have to be released to ask anything;
    # `in_=True` is what restores stdin (global_and_fixture_disabled() leaves it closed).
    capture = config.pluginmanager.getplugin("capturemanager")
    if capture:
        capture.suspend_global_capture(in_=True)
    try:
        answer = input(prompt)
    except (EOFError, OSError):
        answer = ""  # no terminal to ask on
    finally:
        if capture:
            capture.resume_global_capture()
    if answer.strip().lower() not in ("y", "yes"):
        pytest.exit("Aborted.", returncode=1)


@pytest.fixture(scope="module")
def non_native_token(Token, request):
    """
    The token to measure against — ERC20 on Ethereum/Arbitrum, BEP20 on BSC, same
    interface either way. The contract at TOKEN_ADDRESS if given, otherwise conftest's
    `token_minimal` mock, requested lazily so a live run measuring a real token does
    not deploy the mock for nothing.
    """
    address = environ.get("TOKEN_ADDRESS")
    if not address:
        token = request.getfixturevalue("token_minimal")
    else:
        # A plain ERC20/BEP20 ABI covers all that is used: symbol/decimals/balanceOf/transfer.
        try:
            token = Contract.from_abi("Token", address, Token.abi)
        except Exception:
            # brownie raises ContractNotFound when there is no code at the address; a typo
            # in TOKEN_ADDRESS deserves a straight answer, not a fixture traceback.
            pytest.exit(
                f"\nNo contract at TOKEN_ADDRESS {address} on {network.show_active()}.\n",
                returncode=1,
            )
    confirm_live_run(request.config, token)
    return token


@pytest.fixture(scope="module")
def amnt(non_native_token):
    """
    Per-asset amounts. Gas depends only on whether a balance or storage slot crosses
    zero, never on the amount, so keep these small — on a live chain they are real.
    """

    class Amounts:
        local = is_local()
        native = TEST_AMNT if local else 10**12
        token = max(1, 10 ** non_native_token.decimals() // 100)

    return Amounts()


@pytest.fixture(scope="module", autouse=True)
def warm_keyManager(cf_minimal, a, amnt):
    """
    KeyManager's constructor never initialises `_lastValidateTime` (contracts/KeyManager.sol:27-35),
    so the very first `consumeKeyNonce` writes it 0 -> timestamp: a 20k SSTORE plus 2.1k cold
    access, against 5k for every later call. That makes the first measured transaction of the
    module ~17.1k too expensive and unrepresentative of a KeyManager that has been in use.
    Burn one signed call up front so every measurement below is in steady state.
    """
    cf_minimal.SAFEKEEPER.transfer(cf_minimal.vault.address, amnt.native + 1)
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[NATIVE_ADDR, a[8].address, amnt.native]],
    )


def existing_native(cf_minimal, a, amnt, n):
    """Recipients that already exist, on any chain: fund them if they are empty."""
    recipients = [a[i + 1] for i in range(n)]
    for recipient in recipients:
        if recipient.balance() == 0:
            cf_minimal.SAFEKEEPER.transfer(recipient, amnt.native)
    return [r.address for r in recipients]


# ---------------------------------------------------------------- transfers ---


@pytest.mark.parametrize("n", COUNTS)
def test_gas_transfer_native_fresh(cf_minimal, amnt, n):
    """Native egress to an address that does not exist yet (worst case: account creation)."""
    recipients = [fresh_addr("native-fresh", n, i) for i in range(n)]
    cf_minimal.SAFEKEEPER.transfer(cf_minimal.vault.address, amnt.native * (n + 1))
    tx = signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[NATIVE_ADDR, r, amnt.native] for r in recipients],
    )
    record("transfer_native_fresh", n, tx.gas_used)


@pytest.mark.parametrize("n", COUNTS)
def test_gas_transfer_native_existing(cf_minimal, a, amnt, n):
    """Native egress to an address with a non-zero balance (typical case)."""
    recipients = existing_native(cf_minimal, a, amnt, n)
    cf_minimal.SAFEKEEPER.transfer(cf_minimal.vault.address, amnt.native * (n + 1))
    tx = signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[NATIVE_ADDR, r, amnt.native] for r in recipients],
    )
    record("transfer_native_existing", n, tx.gas_used)


@pytest.mark.parametrize("n", COUNTS)
def test_gas_transfer_token_fresh(cf_minimal, non_native_token, amnt, n):
    """Token egress to a holder with a zero balance (worst case: new storage slot)."""
    recipients = [fresh_addr("token-fresh", n, i) for i in range(n)]
    non_native_token.transfer(
        cf_minimal.vault.address,
        amnt.token * (n + 1),
        {"from": cf_minimal.SAFEKEEPER},
    )
    tx = signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[non_native_token.address, r, amnt.token] for r in recipients],
    )
    record("transfer_token_fresh", n, tx.gas_used)


@pytest.mark.parametrize("n", COUNTS)
def test_gas_transfer_token_existing(cf_minimal, non_native_token, a, amnt, n):
    """Token egress to a holder that already has a non-zero balance (typical case)."""
    recipients = [a[i + 1].address for i in range(n)]
    for recipient in recipients:
        if non_native_token.balanceOf(recipient) == 0:
            non_native_token.transfer(
                recipient, amnt.token, {"from": cf_minimal.SAFEKEEPER}
            )
    non_native_token.transfer(
        cf_minimal.vault.address,
        amnt.token * (n + 1),
        {"from": cf_minimal.SAFEKEEPER},
    )
    tx = signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[non_native_token.address, r, amnt.token] for r in recipients],
    )
    record("transfer_token_existing", n, tx.gas_used)


# ------------------------------------------------------------------ fetches ---


@pytest.mark.parametrize("n", COUNTS)
def test_gas_deploy_fetch_native(cf_minimal, Deposit, amnt, n):
    """deployAndFetch of native deposits (Deposit contract CREATE2 + fetch)."""
    params = []
    for i in range(n):
        swap_id = cleanHexStrPad(web3.toHex(0x1000 + n * 16 + i))
        addr = getCreate2Addr(
            cf_minimal.vault.address, swap_id, Deposit, cleanHexStrPad(NATIVE_ADDR)
        )
        cf_minimal.SAFEKEEPER.transfer(addr, amnt.native)
        params.append([swap_id, NATIVE_ADDR])
    tx = signed_call_cf(cf_minimal, cf_minimal.vault.allBatch, params, [], [])
    record("deploy_fetch_native", n, tx.gas_used)


@pytest.mark.parametrize("n", COUNTS)
def test_gas_deploy_fetch_token(cf_minimal, non_native_token, Deposit, amnt, n):
    """deployAndFetch of token deposits, then a plain fetch on the same channels."""
    fetch_params = []
    deploy_params = []
    for i in range(n):
        swap_id = cleanHexStrPad(web3.toHex(0x2000 + n * 16 + i))
        addr = getCreate2Addr(
            cf_minimal.vault.address,
            swap_id,
            Deposit,
            cleanHexStrPad(non_native_token.address),
        )
        non_native_token.transfer(addr, amnt.token, {"from": cf_minimal.SAFEKEEPER})
        deploy_params.append([swap_id, non_native_token.address])
        fetch_params.append([addr, non_native_token.address])

    tx = signed_call_cf(cf_minimal, cf_minimal.vault.allBatch, deploy_params, [], [])
    record("deploy_fetch_token", n, tx.gas_used)

    # Same channels, already deployed -> the plain `fetch` path.
    for addr, _ in fetch_params:
        non_native_token.transfer(addr, amnt.token, {"from": cf_minimal.SAFEKEEPER})
    tx = signed_call_cf(cf_minimal, cf_minimal.vault.allBatch, [], fetch_params, [])
    record("fetch_token_deployed", n, tx.gas_used)


# There is no native equivalent of `fetch_token_deployed` to measure: `Deposit.fetch()`
# is ERC20-only (contracts/Deposit.sol:39-43) and reverts on the native pseudo-address,
# while `receive()` (line 47) forwards later native deposits to the Vault at the
# depositor's expense. That is why the state chain charges no fetch gas for native.


# ---------------------------------------------------------------------- CCM ---

# srcAddress as sent by the state chain for an EVM source chain (20 bytes).
CCM_SRC_CHAIN = 1
CCM_SRC_ADDR = "0x" + "11" * 20

# CCM_VAULT_*_GAS_OVERHEAD is the whole-transaction cost that sits on top of the user's
# gas budget, so the figure to read off is the *total* gas of executexSwapAndCall with a
# receiver that does no real work. A fresh CFTester per case keeps the first (worst case,
# zero -> non-zero token balance slot) call from polluting the next measurement, and the
# second call in each case gives the warm number.


@pytest.mark.parametrize("msg_len", CCM_LENGTHS)
def test_gas_ccm_native(cf_minimal, CFTester, amnt, msg_len):
    """executexSwapAndCall with native: cold receiver then warm receiver."""
    receiver = deploy_new_cfReceiver(
        cf_minimal.SAFEKEEPER, CFTester, cf_minimal.vault.address
    )
    message = "0x" + "ab" * msg_len
    for label in ("cold", "warm"):
        cf_minimal.SAFEKEEPER.transfer(cf_minimal.vault.address, amnt.native * 2)
        tx = signed_call_cf(
            cf_minimal,
            cf_minimal.vault.executexSwapAndCall,
            [NATIVE_ADDR, receiver.address, amnt.native],
            CCM_SRC_CHAIN,
            CCM_SRC_ADDR,
            message,
        )
        record(f"ccm_native_{label}", msg_len, tx.gas_used)


@pytest.mark.parametrize("msg_len", CCM_LENGTHS)
def test_gas_ccm_token(cf_minimal, CFTester, non_native_token, amnt, msg_len):
    """executexSwapAndCall with the token: cold receiver then warm receiver."""
    receiver = deploy_new_cfReceiver(
        cf_minimal.SAFEKEEPER, CFTester, cf_minimal.vault.address
    )
    message = "0x" + "ab" * msg_len
    for label in ("cold", "warm"):
        non_native_token.transfer(
            cf_minimal.vault.address, amnt.token * 2, {"from": cf_minimal.SAFEKEEPER}
        )
        tx = signed_call_cf(
            cf_minimal,
            cf_minimal.vault.executexSwapAndCall,
            [non_native_token.address, receiver.address, amnt.token],
            CCM_SRC_CHAIN,
            CCM_SRC_ADDR,
            message,
        )
        record(f"ccm_token_{label}", msg_len, tx.gas_used)


# ----------------------------------------------------------------- analysis ---

# A line of this sentinel plus one character is rendered as a full-width rule, sized to
# the widest line in the report — so borders never drift when a column or note changes.
RULE = "\x00"


def render(lines):
    # Some lines carry embedded newlines (wrapped prose), so measure physical lines.
    width = max(
        (
            len(part)
            for line in lines
            if not line.startswith(RULE)
            for part in line.split("\n")
        ),
        default=0,
    )
    return "\n".join(
        line[1] * width if line.startswith(RULE) else line for line in lines
    )


SERIES = [
    ("transfer_native_existing", "native -> existing account"),
    ("transfer_native_fresh", "native -> new account"),
    ("transfer_token_existing", "token -> existing holder"),
    ("transfer_token_fresh", "token -> new holder"),
    ("fetch_token_deployed", "token fetch (deployed channel)"),
    ("deploy_fetch_token", "token deployAndFetch"),
    ("deploy_fetch_native", "native deployAndFetch"),
]

CCM_SERIES = [
    ("ccm_native_cold", "native, first-time receiver"),
    ("ccm_native_warm", "native, repeat receiver"),
    ("ccm_token_cold", "token, first-time receiver"),
    ("ccm_token_warm", "token, repeat receiver"),
]


def cells(points, keys, width):
    """One right-aligned column per key, with a dash where a measurement is missing."""
    return "".join(
        f"{points[key]:>{width},}" if key in points else f"{'-':>{width}}"
        for key in keys
    )


def ceil_to(value, step):
    return -(-int(value) // step) * step


def fit(label):
    """Linear fit over n: returns (per_item, base), or None if the series is incomplete."""
    points = RESULTS.get(label, {})
    if 1 not in points or 3 not in points:
        return None
    per_item = (points[3] - points[1]) / 2
    return per_item, points[1] - per_item


def emit(config, token, amnt):
    """Write the analysis via pytest's terminal reporter, which capture never touches."""
    lines = []

    def out(line=""):
        lines.append(line)

    def rule(char="-"):
        lines.append(RULE + char)

    out()
    rule("=")
    out("EVM GAS ANALYSIS")
    out(f"network {network.show_active()} (chainId {chain.id})")
    out(f"token   {token.address} ({token.symbol()}, {token.decimals()} decimals)")
    out(f"amounts {amnt.native:,} wei native, {amnt.token:,} base units of token")
    rule("=")
    out()
    out("allBatch, one item per column count:")
    rule()
    header = "".join(f"{f'n={n}':>10}" for n in COUNTS)
    out(f"{'series':<31}{header}{'per item':>10}{'base':>9}")
    for label, description in SERIES:
        fitted = fit(label)
        if not fitted:
            continue
        per_item, base = fitted
        row = cells(RESULTS[label], COUNTS, 10)
        out(f"{description:<31}{row}{per_item:>10,.0f}{base:>9,.0f}")
    out()
    out("  per item = (n=3 - n=1) / 2;  base = n=1 - per item")
    out("  'new account/holder' is the worst case: account creation / new balance slot")
    out()

    out("executexSwapAndCall total, by message length in bytes:")
    rule()
    header = "".join(f"{f'msg={length}':>10}" for length in CCM_LENGTHS)
    out(f"{'series':<31}{header}{'gas/byte':>10}")
    for label, description in CCM_SERIES:
        points = RESULTS.get(label, {})
        if not points:
            continue
        row = cells(points, CCM_LENGTHS, 10)
        slope = ""
        if 0 in points and 1000 in points:
            slope = f"{(points[1000] - points[0]) / 1000:>10.1f}"
        out(f"{description:<31}{row}{slope}")
    out()
    out("  'first-time receiver' pays the zero -> non-zero token balance slot; the")
    out("  CCM constants are read off the first-time receiver at msg=0")
    out()

    # The state chain charges BASE + PER_ITEM for a single fetch/egress, so the base is
    # the intercept of the cheapest (native-only) batch and every per-item constant is
    # what one worst-case item adds on top of it.
    native_fit = fit("transfer_native_existing")
    if not native_fit:
        out("Not enough data for the constants (run the whole module).")
        write(config, render(lines))
        return

    base_measured = native_fit[1]
    base = ceil_to(base_measured, 10_000)

    derived = [
        (
            "BASE_COST_PER_BATCH",
            base_measured,
            base,
            "'native -> existing' base column, i.e. n=1 - per item",
        )
    ]
    for const, label, note in [
        (
            "GAS_COST_PER_TRANSFER_NATIVE",
            "transfer_native_fresh",
            "'native -> new account' n=1 - base; pays account creation",
        ),
        (
            "GAS_COST_PER_TRANSFER_TOKEN",
            "transfer_token_fresh",
            "'token -> new holder' n=1 - base; pays a new balance slot",
        ),
        (
            "GAS_COST_PER_FETCH",
            "fetch_token_deployed",
            "'token fetch' n=1 - base; excludes the channel deployment",
        ),
    ]:
        if 1 in RESULTS.get(label, {}):
            raw = RESULTS[label][1] - base
            derived.append((const, raw, ceil_to(raw, 1_000), note))
    for const, label, note in [
        (
            "CCM_VAULT_NATIVE_GAS_OVERHEAD",
            "ccm_native_cold",
            "'native, first-time' msg=0; whole tx, receiver included",
        ),
        (
            "CCM_VAULT_TOKEN_GAS_OVERHEAD",
            "ccm_token_cold",
            "'token, first-time' msg=0; whole tx, receiver included",
        ),
    ]:
        if 0 in RESULTS.get(label, {}):
            raw = RESULTS[label][0]
            derived.append((const, raw, ceil_to(raw, 1_000), note))

    out(f"{'constant':<30}{'measured':>10}{'rounded':>9}  notes")
    rule()
    for const, raw, rounded, note in derived:
        out(f"{const:<30}{raw:>10,.0f}{rounded:>9,}  {note}")
    out()
    out("  quoted names are rows of the tables above; n=1/msg=0 are their columns")
    out("  rounded = measured, up to the next 1,000 (10,000 for the base)")
    out()

    # Does BASE + PER_ITEM actually cover the worst case it is meant to cover?
    out("Coverage check — does BASE + PER_ITEM cover the worst case it is charged for?")
    rule()
    out(
        f"  {'':<20}{'base + per item':>19}{'charged':>10}{'worst case':>12}"
        f"{'headroom':>10}"
    )
    charged = {c: r for c, _, r, _ in derived}
    for const, label, what in [
        ("GAS_COST_PER_TRANSFER_NATIVE", "transfer_native_fresh", "native egress"),
        ("GAS_COST_PER_TRANSFER_TOKEN", "transfer_token_fresh", "token egress"),
        ("GAS_COST_PER_FETCH", "fetch_token_deployed", "token fetch"),
    ]:
        if const not in charged or 1 not in RESULTS.get(label, {}):
            continue
        per_item = charged[const]
        total, actual = base + per_item, RESULTS[label][1]
        headroom = total - actual
        verdict = "ok" if headroom >= 0 else "SHORT — raise the constant"
        out(
            f"  {what:<20}{f'{base:,} + {per_item:,}':>19}{total:>10,}{actual:>12,}"
            f"{headroom:>+10,}  {verdict}"
        )
    out()
    out("  worst case = the n=1 column of the rows the constant is read from, i.e. a")
    out("  single-item batch paying account creation / a new balance slot")

    # The state chain adds the base to every item, so anything above one item per batch
    # is over-collected. Worth stating with real numbers: it is the reason a thin
    # headroom above is not as tight as it looks.
    biggest = COUNTS[-1]
    native_points = RESULTS.get("transfer_native_fresh", {})
    if "GAS_COST_PER_TRANSFER_NATIVE" in charged and biggest in native_points:
        per_item = charged["GAS_COST_PER_TRANSFER_NATIVE"]
        batch_charged = biggest * (base + per_item)
        batch_actual = native_points[biggest]
        out(
            f"  the base is charged per item, not per batch, so {biggest} native egresses\n"
            f"  collect {batch_charged:,} against {batch_actual:,} measured "
            f"(+{batch_charged - batch_actual:,} over-collected)"
        )
    out()

    out("Judgement calls the numbers above do NOT make for you:")
    rule()
    out(
        "  * MAX_GAS_LIMIT is a policy cap on how much CCM gas a user can buy, not a\n"
        "    measurement. Compare against the chain's block gas limit and the values\n"
        "    the other EVM chains already use."
    )
    out(
        f"  * The token constants are measured against {token.symbol()} only. A proxy-based\n"
        "    or hooked asset on the same chain costs more — re-run with its TOKEN_ADDRESS."
    )
    native_slope = RESULTS.get("ccm_native_cold", {})
    if 0 in native_slope and 1000 in native_slope:
        per_byte = (native_slope[1000] - native_slope[0]) / 1000
        out(
            f"  * CCM message cost measured at {per_byte:.1f} gas/byte, but"
            " calculate_ccm_gas_limit\n"
            "    adds `+ message_length` (1 gas/byte)."
        )
    out(
        "  * A first deposit costs the deployAndFetch above, while the state chain\n"
        "    collects only BASE (+FETCH for tokens)."
    )
    rule("=")

    write(config, render(lines))


def out_path():
    # Named after the chain it measured: the constants are per-chain, so two runs
    # against different networks must not overwrite each other's report.
    net = "".join(c if c.isalnum() or c in "-_" else "_" for c in network.show_active())
    return f"reports/evm_gas_analysis_{net}_{chain.id}.txt"


def write(config, text):
    # Two routes to the reader, because either one can be swallowed: pytest's terminal
    # reporter (never captured, but buried in docker's output), and a file on the bind
    # mount that `make estimate_gas` cats on the host afterwards.
    with open(environ.get("GAS_ANALYSIS_OUT", out_path()), "w") as f:
        f.write(text + "\n")
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter:
        reporter.write_line(text)


@pytest.fixture(scope="module", autouse=True)
def analysis(request, non_native_token, amnt):
    yield
    emit(request.config, non_native_token, amnt)
