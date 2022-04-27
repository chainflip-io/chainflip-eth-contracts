import sys
import os

sys.path.append(os.path.abspath("tests"))
from consts import *

from brownie import accounts, web3


CHAINFLIP_SEED = os.environ["CHAINFLIP_SEED"]
# Annoyingly you need to use cf_accs in order to access the private keys directly,
# they can't be found via accounts[0] etc since it doesn't replace the accounts
# and the private keys of the default accounts can't be accessed directly
cf_accs = accounts.from_mnemonic(CHAINFLIP_SEED, count=10)

# Need to send ETH to cf_accs so that the 'succeeding' tx can actually succeed,
# because it has no ETH by default
accounts[0].transfer(cf_accs[0], "1 ether")


def _gen_tx(from_acc, to_acc, amount):
    signed_tx = web3.eth.account.sign_transaction(
        dict(
            nonce=web3.eth.get_transaction_count(from_acc.address),
            gas=21000,
            gasPrice=web3.eth.gas_price,
            to=to_acc.address,
            value=amount,
            data=b"",
        ),
        from_acc.private_key,
    )

    print(signed_tx.rawTransaction.hex())
    # print(web3.eth.send_raw_transaction(signed_tx.rawTransaction))
    print()


def gen_succeed_and_fail():
    from_acc = cf_accs[0]
    to_acc = cf_accs[1]
    amount = 12345
    print(
        f"A successful tx that will send {amount / 10**18} ETH from {from_acc.address} to {to_acc.address}:"
    )
    _gen_tx(from_acc, to_acc, amount)

    from_acc = cf_accs[0]
    to_acc = cf_accs[2]
    amount = 10**3 * E_18
    print(
        f"A reverting tx that will fail trying to send {amount / 10**18} ETH from {from_acc.address} to {to_acc.address}:"
    )
    _gen_tx(from_acc, to_acc, amount)
