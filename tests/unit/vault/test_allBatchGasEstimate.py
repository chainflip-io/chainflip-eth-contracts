"""
Gas measurements for the state-chain fee constants of any secondary EVM chain
(chainflip-backend state-chain/chains/src/<chain>.rs, `pub mod fees`).

The state chain models a fetch/egress as:
    gas = BASE_COST_PER_BATCH + n * GAS_COST_PER_<item>
so a single-item batch cannot separate the intercept from the slope. Every measurement
below therefore runs at n = 1, 2, 3 in one `allBatch`: the slope is the per-item constant
and the intercept is the batch base cost. The analysis at the end of the module derives
every constant and prints it, including a coverage check of its own output.

The CCM measurements (CCM_VAULT_*_GAS_OVERHEAD) are OFF by default — they deploy a
CFTester per case and are only needed when those two constants are being set. Turn them
on with CCM=1 in the environment (`make estimate_gas CCM=1`); everything else always runs.

Local (mock ERC20 from conftest's `token_minimal`, no real funds needed):

    brownie test tests/unit/vault/test_allBatchGasEstimate.py --network hardhat --stateful false

Live network, measuring against the chain's real token contract:

    export SEED="<mnemonic funded with the gas asset AND the token>"
    export TOKEN_ADDRESS=0x55d398326f99059fF775485246999027B3197955   # BSC-USDT
    export CCM=1                                                     # optional
    brownie test tests/unit/vault/test_allBatchGasEstimate.py --network bsc-main --stateful false

PICK A LOW-VALUE TOKEN — a stablecoin. Amounts are 1% of one whole token (scaled by
decimals()) because token gas depends on decimals and on whether a balance slot crosses
zero, never on value. A run moves 0.33 of a token out of the account (0.45 with CCM=1, in
transfers of 0.01) and strands 0.06 of it (0.12 with CCM=1) in hash-derived addresses and
CFTester contracts: cents in USDT, hundreds of dollars in WBTC.

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

# The CCM measurements are opt-in: they deploy a CFTester per case and are only wanted
# when CCM_VAULT_*_GAS_OVERHEAD is being set, so a plain fetch/egress run skips them.
MEASURE_CCM = environ.get("CCM", "").strip().lower() in ("1", "true", "yes", "on")
ccm_only = pytest.mark.skipif(
    not MEASURE_CCM, reason="CCM measurements are opt-in: set CCM=1 to run them"
)

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
    return web3.toChecksumAddress(
        web3.keccak(text=f"{RECIPIENT_SALT}-{tag}-{n}-{i}")[-20:].hex()
    )


def is_local():
    return chain.id in [hardhat, eth_localnet, arb_localnet]


def confirm_live_run(config, token):
    """Confirm before touching a live chain: this run spends real gas and real tokens."""
    if is_local():
        return
    # The CCM cases account for 0.12 of the token spend (0.06 of it stranded in the
    # CFTesters, 0.06 left in the Vault), so the figures quoted differ with the flag.
    ccm = " and one CFTester per CCM case" if MEASURE_CCM else ""
    total, stranded, vault = (
        ("0.45", "0.12", "0.24") if MEASURE_CCM else ("0.33", "0.06", "0.18")
    )
    prompt = (
        f"\nLive run on {network.show_active()} (chainId {chain.id}) with "
        f"{token.symbol()} at {token.address}."
        f"\nIt deploys its own KeyManager/Vault/AddressChecker{ccm} and moves {total}"
        f" {token.symbol()} plus gas out of this account: {stranded} stranded (fresh"
        f" recipients{', CFTesters' if MEASURE_CCM else ''}), retrievable {vault} in the"
        f" Vault it deploys and 0.09 in your own SEED accounts. Continue? [y/N]: "
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

# What an implementer following the docs budgets: eth_estimateGas of a direct cfReceive
# call, from the Vault, minus the 21,000 intrinsic cost. Measured at every message length
# so the analysis can subtract its slope from the Vault's: the difference is the per-byte
# cost the state chain has to add, and everything below it is already in gas_budget.
EVM_BASE_GAS_LIMIT = 21_000


def user_budget(cf_minimal, receiver, token, amount, message, value=0):
    estimate = receiver.cfReceive.estimate_gas(
        CCM_SRC_CHAIN,
        CCM_SRC_ADDR,
        message,
        token,
        amount,
        {"from": cf_minimal.vault.address, "value": value},
    )
    return estimate - EVM_BASE_GAS_LIMIT


@ccm_only
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

    # Warm receiver, i.e. the same state the user's own estimateGas would see.
    record(
        "ccm_native_user_budget",
        msg_len,
        user_budget(
            cf_minimal,
            receiver,
            NATIVE_ADDR,
            amnt.native,
            message,
            value=amnt.native,
        ),
    )


@ccm_only
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

    record(
        "ccm_token_user_budget",
        msg_len,
        user_budget(
            cf_minimal, receiver, non_native_token.address, amnt.token, message
        ),
    )


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
    ("ccm_native_user_budget", "  native, user's estimateGas budget"),
    ("ccm_token_cold", "token, first-time receiver"),
    ("ccm_token_warm", "token, repeat receiver"),
    ("ccm_token_user_budget", "  token, user's estimateGas budget"),
]


def cells(points, keys, width):
    """One right-aligned column per key, with a dash where a measurement is missing."""
    return "".join(
        f"{points[key]:>{width},}" if key in points else f"{'-':>{width}}"
        for key in keys
    )


def ceil_to(value, step):
    return -(-int(value) // step) * step


def slope(label):
    """Gas per message byte for a CCM series, or None if it was not measured."""
    points = RESULTS.get(label, {})
    lo, hi = CCM_LENGTHS[0], CCM_LENGTHS[-1]
    if lo not in points or hi not in points:
        return None
    return (points[hi] - points[lo]) / (hi - lo)


def fit(label):
    """Linear fit over n: returns (per_item, base), or None if the series is incomplete."""
    points = RESULTS.get(label, {})
    if 1 not in points or 3 not in points:
        return None
    per_item = (points[3] - points[1]) / 2
    return per_item, points[1] - per_item


# The state chain adds `+ message_length` (1 gas/byte) on top of the user's gas_budget
# for "the extra gas overhead of passing the message through the Vault". The gas/byte
# column above is NOT that number: it is the whole per-byte cost, most of which the user
# already bought (their own transaction's calldata, their receiver's work on the message).
# Only the difference between the two slopes is the Vault's, and that is what the state
# chain's constant should be.
CCM_MESSAGE_PAIRS = [
    ("native", "ccm_native_warm", "ccm_native_user_budget"),
    ("token", "ccm_token_warm", "ccm_token_user_budget"),
]


def emit_message_overhead(out, rule):
    rows = [
        (asset, slope(vault_label), slope(user_label))
        for asset, vault_label, user_label in CCM_MESSAGE_PAIRS
    ]
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    if not rows:
        return

    out("Per message byte — how much of it is actually the Vault's overhead?")
    rule()
    out(
        f"  {'':<12}{'vault total':>13}{'estimateGas budget':>20}"
        f"{'vault overhead':>16}{'charged':>10}"
    )
    worst = 0.0
    for asset, vault_per_byte, user_per_byte in rows:
        overhead = vault_per_byte - user_per_byte
        worst = max(worst, overhead)
        out(
            f"  {asset:<12}{vault_per_byte:>13.1f}{user_per_byte:>20.1f}"
            f"{overhead:>16.1f}{1:>10}"
        )
    out()
    out(
        "  vault overhead = vault total - user's estimateGas budget, per byte of message"
    )
    if worst > 1:
        out(
            f"  The state chain adds 1 gas/byte; the Vault's own overhead measures"
            f" {worst:.1f}\n"
            f"  gas/byte, so `+ message_length` UNDER-collects by {worst - 1:.1f} gas/byte"
            f"\n  ({(worst - 1) * CCM_LENGTHS[-1]:,.0f} gas on a {CCM_LENGTHS[-1]}-byte"
            " message). Raise the multiplier."
        )
    else:
        out(
            f"  The state chain adds 1 gas/byte and the Vault's own overhead measures"
            f" {worst:.1f}\n  gas/byte, so `+ message_length` covers it."
        )
    out()


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

    if any(RESULTS.get(label) for label, _ in CCM_SERIES):
        out("executexSwapAndCall total, by message length in bytes:")
        rule()
        header = "".join(f"{f'msg={length}':>10}" for length in CCM_LENGTHS)
        out(f"{'series':<35}{header}{'gas/byte':>10}")
        for label, description in CCM_SERIES:
            points = RESULTS.get(label, {})
            if not points:
                continue
            row = cells(points, CCM_LENGTHS, 10)
            per_byte = slope(label)
            out(
                f"{description:<35}{row}"
                f"{'' if per_byte is None else f'{per_byte:>10.1f}'}"
            )
        out()
        out("  'first-time receiver' pays the zero -> non-zero token balance slot; the")
        out("  CCM constants are read off the first-time receiver at msg=0")
        out(
            '  "user\'s estimateGas budget" is eth_estimateGas of a direct cfReceive call'
        )
        out(
            f"  from the Vault minus {EVM_BASE_GAS_LIMIT:,} — the gas_budget the docs"
            " tell implementers to buy"
        )
        out()
        emit_message_overhead(out, rule)
    else:
        # Say it outright: a missing CCM_VAULT_* below is a flag that was off, not a
        # measurement that came back empty.
        out("executexSwapAndCall was NOT measured (CCM=1 turns it on), so the two")
        out("CCM_VAULT_*_GAS_OVERHEAD constants are absent below.")
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
    if slope("ccm_native_user_budget") is not None:
        out(
            "  * The per-byte table assumes implementers actually follow the docs and\n"
            "    estimateGas their own cfReceive. One that hardcodes a gas_budget buys\n"
            "    none of the per-byte cost, and no state-chain constant can fix that."
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
