from os import environ
from brownie import accounts, StakeManager, FLIP

AUTONOMY_SEED = environ['SEED']
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

node_ids = [
	"Enter Node IDs here in hex format"
]

flip = FLIP.at("FLIP_TOKEN_ADDRESS")
stakeManager = StakeManager.at("STAKE_MANAGER_ADDRESS")

stake = 45000 * (10**18)
return_addr = "0xffffffffffffffffffffffffffffffffffffffff"

def main():
	staker = cf_accs[0]
	to_approve = stake * (len(node_ids) + 1)
	tx = flip.approve(stakeManager, to_approve, {"from": staker, "required_confs": 0})
	print(f'Approving {to_approve / 10**18} FLIP in tx {tx.txid}')
	for i, node_id in enumerate(node_ids):
		to_stake = stake + (i * 10**18)
		tx = stakeManager.stake(node_id, to_stake, return_addr, {"from": staker, "required_confs": 0})
		print(f'Staking {to_stake / 10**18} FLIP in tx {tx.txid}')

