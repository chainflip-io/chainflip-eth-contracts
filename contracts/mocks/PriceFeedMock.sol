pragma solidity ^0.8.0;

/**
 * @title    Chainlink AggregatorProxy Mock
 * @dev      Mock of the Chainlink Price Feed Aggregator program.
 */

interface AggregatorV3Interface {
    function decimals() external view returns (uint8);

    function version() external view returns (uint256);

    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract PriceFeedMock is AggregatorV3Interface {
    uint8 private _decimals;
    uint256 private _version;

    uint80 private _roundId;
    int256 private _answer;
    uint256 private _startedAt;
    uint256 private _updatedAt;
    uint80 private _answeredInRound;

    /**
     * @notice get data about the latest round. Consumers are encouraged to check
     * that they're receiving fresh data by inspecting the updatedAt and
     * answeredInRound return values.
     * Note that different underlying implementations of AggregatorV3Interface
     * have slightly different semantics for some of the return values. Consumers
     * should determine what implementations they expect to receive
     * data from and validate that they can properly handle return data from all
     * of them.
     * @return roundId is the round ID from the aggregator for which the data was
     * retrieved combined with an phase to ensure that round IDs get larger as
     * time moves forward.
     * @return answer is the answer for the given round
     * @return startedAt is the timestamp when the round was started.
     * (Only some AggregatorV3Interface implementations return meaningful values)
     * @return updatedAt is the timestamp when the round last was updated (i.e.
     * answer was last computed)
     * @return answeredInRound is the round ID of the round in which the answer
     * was computed.
     * (Only some AggregatorV3Interface implementations return meaningful values)
     * @dev Note that answer and updatedAt may change between queries.
     */
    function latestRoundData()
        public
        view
        override
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    {
        (roundId, answer, startedAt, updatedAt, answeredInRound) = (
            _roundId,
            _answer,
            _startedAt,
            _updatedAt,
            _answeredInRound
        );
    }

    /**
     * @notice represents the number of decimals the aggregator responses represent.
     */
    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    /**
     * @notice the version number representing the type of aggregator the proxy
     * points to.
     */
    function version() external view override returns (uint256) {
        return _version;
    }

    /**
     * @notice Added mock functions to update the values
     */
    function updatePriceFeed(
        uint80 newRoundId,
        int256 newAnswer,
        uint256 newStartedAt,
        uint256 newUpdatedAt,
        uint80 newAnsweredInRound
    ) external {
        _roundId = newRoundId;
        _answer = newAnswer;
        _startedAt = newStartedAt;
        _updatedAt = newUpdatedAt;
        _answeredInRound = newAnsweredInRound;
    }

    function updateSettings(uint8 newDecimals, uint256 newVersion) external {
        _decimals = newDecimals;
        _version = newVersion;
    }
}
