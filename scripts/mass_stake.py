from os import environ
from brownie import accounts, StakeManager, FLIP

FLIP_ADDRESS = environ['FLIP_ADDRESS']
STAKE_MANAGER_ADDRESS = environ['STAKE_MANAGER_ADDRESS']
AUTONOMY_SEED = environ['SEED']
NODE_ID_FILE = environ['NODE_ID_FILE']

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

node_ids = []

flip = FLIP.at(f'0x{FLIP_ADDRESS}')
stakeManager = StakeManager.at(f'0x{STAKE_MANAGER_ADDRESS}')

stake = 45000 * (10**18)
return_addr = "0xffffffffffffffffffffffffffffffffffffffff"

def main():
	with open(NODE_ID_FILE, 'r') as f:
		node_ids = f.readlines()
		f.close()
	staker = cf_accs[0]
	to_approve = stake * (len(node_ids) + 1)
	tx = flip.approve(stakeManager, to_approve, {"from": staker, "required_confs": 0})
	print(f'Approving {to_approve / 10**18} FLIP in tx {tx.txid}')
	for i, node_id in enumerate(node_ids):
		to_stake = stake + (i * 10**18)
		node_id = node_id.strip()
		tx = stakeManager.stake(node_id, to_stake, return_addr, {"from": staker, "required_confs": 0})
		print(f'Staking {to_stake / 10**18} FLIP to node {node_id} in tx {tx.txid}')

