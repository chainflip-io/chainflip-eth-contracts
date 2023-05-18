slither-flat contracts/echidna/tests/NewTestEchidna.sol --solc-remaps @openzeppelin=node_modules/@openzeppelin
cp crytic-export/flattening/NewTestEchidna_*.sol contracts/echidna/tests/NewTestEchidna-flat.sol
rm -rf crytic-export
echidna contracts/echidna/tests/NewTestEchidna-flat.sol --contract NewTestEchidna --config contracts/echidna/tests/echidna-assertion.config.yml

