// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

contract PriceOracle {
    AggregatorV3Interface public primaryFeed;
    AggregatorV3Interface public fallbackFeed;
    address public owner;
    uint256 public MAX_STALENESS = 3600;

    event PriceQueried(int256 price, uint256 timestamp);
    event StalePrice(address primaryFeed, uint256 lastUpdated, address fallbackFeed);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _primaryFeed, address _fallbackFeed) {
        primaryFeed = AggregatorV3Interface(_primaryFeed);
        fallbackFeed = AggregatorV3Interface(_fallbackFeed);
        owner = msg.sender;
    }

    function getLatestPrice() external view returns (int256) {
        // Try primary oracle first
        (int256 price, bool valid) = _tryGetPriceFromOracle(primaryFeed);
        if (valid && price > 0) {
            return price;
        }

        // Primary stale/invalid, emit event and try fallback
        emit StalePrice(address(primaryFeed), 0, address(fallbackFeed));

        (price, valid) = _tryGetPriceFromOracle(fallbackFeed);
        require(valid && price > 0, "Both oracles stale or invalid");

        return price;
    }

    function _tryGetPriceFromOracle(AggregatorV3Interface feed) internal view returns (int256 price, bool valid) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = feed.latestRoundData();

        if (answer <= 0) return (0, false);
        if (answeredInRound < roundId) return (0, false);
        if (block.timestamp - updatedAt >= MAX_STALENESS) return (0, false);

        return (answer, true);
    }

    function getDecimals() external view returns (uint8) {
        return primaryFeed.decimals();
    }

    function setMaxStaleness(uint256 _maxStaleness) external onlyOwner {
        MAX_STALENESS = _maxStaleness;
    }

    function setFallbackFeed(address _fallbackFeed) external onlyOwner {
        fallbackFeed = AggregatorV3Interface(_fallbackFeed);
    }
}
