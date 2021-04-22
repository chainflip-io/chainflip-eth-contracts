# from consts import *
# from shared_tests import *
# from brownie import reverts, web3, chain
# from brownie.test import given, strategy


# # @given(
# #     amount=strategy('uint', max_value=MIN_STAKE*2),
# #     staker=strategy('address'),
# #     expiryTimeDiff=strategy('uint', max_value=int(30*DAY/SECS_PER_BLOCK))
# # )
# # def test_registerClaim_amount_rand(cf, stakedMin, amount, staker, expiryTimeDiff):


# def test_executeClaim(cf, claimRegistered):
#     _, claim = claimRegistered
#     assert cf.stakeManager.getPendingClaim(JUNK_INT) == claim

#     tx = cf.stakeManager.executeClaim(JUNK_INT)

#     assert cf.stakeManager.getPendingClaim(JUNK_INT) == NULL_CLAIM
    