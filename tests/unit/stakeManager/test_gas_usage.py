# from consts import *
# from brownie import chain


# def test_transfer(a, cfDeploy):
#     tx = cfDeploy.flip.transfer(a[1], TEST_AMNT, {'from': a[0]})
#     print(f'Transfer: {tx.gas_used}')


# def test_send(a, cfDeploy):
#     tx = cfDeploy.flip.send(a[1], TEST_AMNT, "", {'from': a[0]})
#     print(f'Send: {tx.gas_used}')


# def test_stake(a, cfDeploy):
#     tx = cfDeploy.stakeManager.stake(JUNK_INT, MIN_STAKE, {'from': a[0]})
#     print(f'Stake: {tx.gas_used}')


# def test_executeClaim(a, cfDeploy):
#     args = (JUNK_INT, TEST_AMNT, a[0], chain.time() + CLAIM_DELAY + 10)
#     callDataNoSig = cfDeploy.stakeManager.registerClaim.encode_input(NULL_SIG_DATA, *args)
#     cfDeploy.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args, {'from': a[0]})

#     chain.sleep(CLAIM_DELAY)
#     tx = cfDeploy.stakeManager.executeClaim(JUNK_INT, {'from': a[0]})
#     print(f'executeClaim: {tx.gas_used}')


# def test_setEmissionPerBlock(a, cfDeploy):
#     callDataNoSig = cfDeploy.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, JUNK_INT)
#     tx = cfDeploy.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), JUNK_INT, {'from': a[0]})
#     print(f'setEmissionPerBlock: {tx.gas_used}')