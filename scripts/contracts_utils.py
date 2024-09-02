import sys
import os

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import accounts, KeyManager, Vault, network
from shared_tests import *
import re

# These functions are utils functions to replay, simulate or decode transactions crafted by the State Chain. These can
# be transactions that aborted, reverted or failed for any other reason. Also it can decode raw bytes calls.
# It can be used for calls to the Vault and/or to the Key Manager.

# When making the calls you should replace the addresses of the contracts with the ones for the network you are using.
# Also, insert the adequate values that you want to decode/broadcast.
# Finally, you can add `.call` to simulate the transaction without broadcasting it. Remove it to broadcast the transaction.

# Run with `brownie run contracts_utils <function_name> --network hardhat/mainnet/arbitrum-main`

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")


network.priority_fee("1 gwei")

# Decode raw bytes call to the Vault contract. This is useful when a broadcast aborts and we have the raw bytes.
# However, the engine logs should also be reporting what the error was.
def decode_vault_call():
    # Insert call bytes. E.g. [82, 147, 23, 142, 164, ...]
    bytes = [0]

    hex_string = "".join(hex(num)[2:].zfill(2) for num in bytes)
    # print("0x" + hex_string)
    print(Vault.decode_input(hex_string))


# Decode raw bytes call to the Key Manager contract: This is useful when a broadcast aborts and we have the raw bytes.
# However, the engine logs should also be reporting what the error was.
def decode_keymanager_call():
    # Insert call bytes. E.g. [193, 196, 161, 89, 183, ...]
    bytes = [0]

    hex_string = "".join(hex(num)[2:].zfill(2) for num in bytes)
    # print("0x" + hex_string)
    print(KeyManager.decode_input(hex_string))


# Send a transfer fallback call to the Vault contract. That is to be used to replay a CCM message that has aborted.
def send_transferFallback():
    # Insert the address of the vault contract for the network
    vault = Vault.at("0xF5e10380213880111522dd0efD3dbb45b9f62Bcc")

    # Get the sig data from the signed tx. Will look like this and can be converted straight away to a uint.
    # sig: 105,443,778,774,230,036,821,222,798,164,959,664,336,048,410,063,990,219,863,188,006,721,837,015,465,009
    sig = 105443778774230036821222798164959664336048410063990219863188006721837015465009
    nonce = 7227
    kTimesGAddress = "0x6c87aef85c3342deaecc056aecaf62f61af62233"

    # Insert [token, recipitent, amount]
    transferParams = [
        NATIVE_ADDR,
        "0xf112f5d0995e17bfe5021fea90c3a6fac875664e",
        39085318502136655,
    ]

    sigData = [
        sig,
        nonce,
        kTimesGAddress,
    ]

    tx = vault.transferFallback(sigData, transferParams, {"from": DEPLOYER})
    tx.info()


def send_allBatch():
    # Insert the address of the vault contract for the network
    vault = Vault.at("0x2bb150e6d4366A1BDBC4275D1F35892CD63F27e3")

    # Get the sig data from the signed tx as in the send_transferFallback function.
    sigData = [
        53564996668499050857217723416332709030557380600265126346613536706207704396933,
        584,
        "0xd1714973cbd82edad9c1af48cb21abd54283e366",
    ]
    # [token, recipitent, amount]
    transferParams = [
        NATIVE_ADDR,
        "0x8c952cc18969129a1c67297332a0b6558eb0bfec",
        428007866314266787,
    ]

    tx = vault.allBatch(sigData, [], [], [transferParams], {"from": DEPLOYER})
    tx.info()


def send_rotation():
    # Insert the address of the Key Manager contract for the network
    keyManager = KeyManager.at("0x18195b0E3c33EeF3cA6423b1828E0FE0C03F32Fd")

    # Get the sig data from the signed tx as in the send_transferFallback function.
    sigData = [
        15744132089818751460223478396489526259646805948031235684624463192235106336468,
        587,
        "0x9b5cc915cfb363c0dbf7ee25caee6261cfb8d4bd",
    ]

    tx = keyManager.setAggKeyWithAggKey(
        sigData,
        (
            19461722762821367710032909336806588856719894271958382684299865054750972487645,
            0,
        ),
        {"from": DEPLOYER},
    )
    tx.info()


# Parse file with the `transactionOutIdToBroadcastId`
# That should be a list like this [[[{s: string, kTimesGAddress: string}],[broadcastId, blockNumber]], ...]
def parse_text():
    # Insert the path to the file
    file_path = "file.txt"
    pairs = []

    with open(file_path, "r") as file:
        s_value = None
        kTimesGAddress_value = None

        for line in file:
            # Strip leading/trailing whitespace
            line = line.strip()

            # Check for the 's:' line
            if line.startswith("s:"):
                s_value = line.split("s:")[1].strip()

            # Check for the 'kTimesGAddress:' line
            elif "kTimesGAddress:" in line:
                kTimesGAddress_value = line.split("kTimesGAddress:")[1].strip()

            # Check for the line with the number (e.g., 500)
            elif line.isdigit():
                number = int(line)

                # Ensure both s and kTimesGAddress have been captured
                if s_value and kTimesGAddress_value:
                    pairs.append(
                        (number, {"s": s_value, "kTimesGAddress": kTimesGAddress_value})
                    )

                    # Reset s_value and kTimesGAddress_value after pairing
                    s_value = None
                    kTimesGAddress_value = None

    # Sort it by broadcast id
    pairs.sort(key=lambda x: x[0])

    broadcastID = 502
    # Get nonce and newAggKey from pendingApiCalls for that broadcastId
    nonce = 564
    newAggKey = (
        16960693264591855940648150423704738328849124419851104914880108972622132112107,
        0,
    )

    filtered_pairs = [pair for pair in pairs if pair[0] == broadcastID]

    keyManager = KeyManager.at("0x18195b0E3c33EeF3cA6423b1828E0FE0C03F32Fd")

    loop_counter = 0
    for _, data in filtered_pairs:
        loop_counter += 1
        print(f"Loop number: {loop_counter}")

        # Convert hexadecimal 's' value to decimal and extract  'kTimesGAddress'
        s_decimal = int(data["s"], 16)
        kTimesGAddress = data["kTimesGAddress"]

        sigData = [s_decimal, nonce, kTimesGAddress]
        try:
            # Use "call" to simulate the transaction. Remove it to broadcast the transaction.
            tx = keyManager.setAggKeyWithAggKey.call(
                sigData, newAggKey, {"from": DEPLOYER}
            )
            # tx = keyManager.setAggKeyWithAggKey(sigData, newAggKey, {"from": DEPLOYER})
            print("Transaction simulation succeeded")
            print(tx)
            break
        except Exception as e:
            print("Transaction simulation failed")
            print(f"Error: {e}")
