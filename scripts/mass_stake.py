from os import environ
from brownie import accounts, StakeManager, FLIP

FLIP_ADDRESS = environ['FLIP_ADDRESS']
STAKE_MANAGER_ADDRESS = environ['STAKE_MANAGER_ADDRESS']
AUTONOMY_SEED = environ['SEED']

# File should be formatted as a list of NODE_IDs separated by a newline
NODE_ID_FILE = environ['NODE_ID_FILE']

DEPLOYER_ACCOUNT_INDEX = int(environ.get('DEPLOYER_ACCOUNT_INDEX') or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

node_ids = []

stake = 1000 * (10**18)
return_addr = "0xffffffffffffffffffffffffffffffffffffffff"

def main():
	flip = FLIP.at(f'0x{cleanHexStr(FLIP_ADDRESS)}')
	stakeManager = StakeManager.at(f'0x{cleanHexStr(STAKE_MANAGER_ADDRESS)}')
	with open(NODE_ID_FILE, 'r') as f:
		node_ids = f.readlines()
		f.close()
	staker = cf_accs[DEPLOYER_ACCOUNT_INDEX]
	to_approve = stake * (len(node_ids) + 1)
	tx = flip.approve(stakeManager, to_approve, {"from": staker, "required_confs": 0})
	print(f'Approving {to_approve / 10**18} FLIP in tx {tx.txid}')
	for i, node_id in enumerate(node_ids):
		to_stake = stake + (i * 10**18)
		node_id = node_id.strip()
		tx = stakeManager.stake(node_id, to_stake, return_addr, {"from": staker, "required_confs": 0})
		print(f'Staking {to_stake / 10**18} FLIP to node {node_id} in tx {tx.txid}')

def cleanHexStr(thing):
	if isinstance(thing, int):
		thing = hex(thing)
	elif not isinstance(thing, str):
		thing = thing.hex()
	return thing[2:] if thing[:2] == "0x" else thing