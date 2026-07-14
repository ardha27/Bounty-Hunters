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
    event FallbackUsed();

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _primaryFeed) {
        primaryFeed = AggregatorV3Interface(_primaryFeed);
        owner = msg.sender;
    }

    function setFallbackFeed(address _fallbackFeed) external onlyOwner {
        fallbackFeed = AggregatorV3Interface(_fallbackFeed);
    }

    function _validateFeed(AggregatorV3Interface feed, string memory prefix) internal view returns (int256 price, uint256 updatedAt) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 feedUpdatedAt,
            uint80 answeredInRound
        ) = feed.latestRoundData();

        require(answer > 0, string.concat(prefix, "invalid price"));
        require(answeredInRound >= roundId, string.concat(prefix, "stale round"));
        require(feedUpdatedAt > 0, string.concat(prefix, "incomplete round"));
        require(block.timestamp - feedUpdatedAt <= MAX_STALENESS, string.concat(prefix, "price stale"));

        return (answer, feedUpdatedAt);
    }

    function getLatestPrice() external view returns (int256) {
        (int256 price, ) = _validateFeed(primaryFeed, "");
        return price;
    }

    function getLatestPriceWithFallback() external view returns (int256) {
        try this.getLatestPrice() returns (int256 price) {
            return price;
        } catch {
            require(address(fallbackFeed) != address(0), "No fallback oracle");
            (int256 price, ) = _validateFeed(fallbackFeed, "fallback: ");
            return price;
        }
    }

    function getDecimals() external view returns (uint8) {
        return primaryFeed.decimals();
    }

    function setMaxStaleness(uint256 _maxStaleness) external onlyOwner {
        MAX_STALENESS = _maxStaleness;
    }
}
