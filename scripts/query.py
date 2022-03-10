from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP

flip = FLIP.at("0x2822d24137073632AA367daA84671100da631187")

print(flip.totalSupply())
