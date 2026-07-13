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
    event FallbackUsed(uint256 primaryUpdatedAt, uint256 primaryRoundId);
    event FallbackSet(address oldFeed, address newFeed);

    constructor(address _primaryFeed) {
        primaryFeed = AggregatorV3Interface(_primaryFeed);
        owner = msg.sender;
    }

    function setFallbackFeed(address _fallbackFeed) external {
        require(msg.sender == owner, "Not owner");
        address old = address(fallbackFeed);
        fallbackFeed = AggregatorV3Interface(_fallbackFeed);
        emit FallbackSet(old, _fallbackFeed);
    }

    function getLatestPrice() external view returns (int256) {
        // Try primary feed
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = primaryFeed.latestRoundData();

        bool primaryValid = (price > 0) &&
            (answeredInRound >= roundId) &&
            (block.timestamp - updatedAt < MAX_STALENESS);

        if (primaryValid) {
            return price;
        }

        // Fallback to secondary feed if configured
        if (address(fallbackFeed) != address(0)) {
            emit FallbackUsed(updatedAt, roundId);

            (roundId, price, , updatedAt, answeredInRound) =
                fallbackFeed.latestRoundData();

            require(price > 0, "Fallback: non-positive price");
            require(answeredInRound >= roundId, "Fallback: stale round");
            require(
                block.timestamp - updatedAt < MAX_STALENESS,
                "Fallback: stale price"
            );
            return price;
        }

        revert("No valid price available");
    }

    function getDecimals() external view returns (uint8) {
        return primaryFeed.decimals();
    }

    function setMaxStaleness(uint256 _maxStaleness) external {
        require(msg.sender == owner, "Not owner");
        MAX_STALENESS = _maxStaleness;
    }
}
