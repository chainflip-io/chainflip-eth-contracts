# Fuzzing with Echidna

Echidna: https://github.com/crytic/echidna

Basic guide: https://github.com/crytic/building-secure-contracts/tree/master/program-analysis/echidna#echidna-tutorial

Fuzzing is used here to to try and find bugs that arise from complex interactions both between functions in the same contract and functions of different contracts. The main difference between fuzzing and brownie stateful tests is that Echidna generates random input values for external/public functions. Then different test modes can be used to test the outcome of the function calls. This can be specified in the echidna configuration file.

Echidna allows to easily test properties, revertion of function calls and assertions. For a more in depth explanation please refer to the Basic Guide.

Our contracts are not a perfect target for fuzzing due to the low amount of state variables (storage) and a high amount of calls that require a valid signature. Calls that require a valid signature get reverted and given that fuzzing generates random inputs, all those calls revert. However, this result itself is useful to assess that the signature mechanism cannot be easily brute-forced.

Externally keeping track of all the calls (e.g. registered claims, amount staked..) is exactly what we do in the brownie stateful test. Replicating the same methodology is unnecessary. Therefore, the fuzzing does no intend to test all scenarios, it is more a health check testing the signed functions reversion and the basic governance and community function calls.

There are some workarounds that have been done to get it working. First, we have several contracts that depend on each other. They are not isolated and need to be tested together. This makes the process more cumbersome since echidna is extremely limited in that regard and does not allow us to use the deployment script. To circumvent that we have created a deployer contract that deploys the other contracts on the constructor mimicking the deployment script.

A limitation caused by the previous solution is that deploying all contracts from the deployer makes it so Echidna does not see all the external functions of the contracts. Therefore, a *Echidna.sol contracts have been created as a way to expose all the external functions to Echidna so it fuzzes them. The test files then inherit from those contracts.

Finally, Echidna does not suppport constructors with parameters. Therefore, the parameters needed for all the contracts' constructors have been hardcoded in every test and then passed to the remaining constructors. This way the top level test contract has no constructor parameters. The constructor parameters need to be changed in the Deployer or the test if any constructor parameters need to be changed.

Note: Do not add both slither and slither analyzer to poetry. That get installed correctly (no error or warnings) but when executing the tool it gives errors about missing packages.

Note2: Dependencies that require the node_modules contract folder (inherited openZeppelin contracts) are not detected by Echidna throwing a nasty error. It doesn't understand that those dependencies are under node_modules. Therefore, any dependencies need to be copied to the root folder so the paths match.