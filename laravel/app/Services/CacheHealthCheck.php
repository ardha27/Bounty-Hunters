<?php

namespace App\Services;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Config;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;

class CacheHealthCheck
{
    /**
     * Test the connection for the active cache store.
     *
     * @return array{available: bool, driver: string, latency_ms: float|null, error: string|null}
     */
    public static function check(): array
    {
        $driver = Config::get('cache.default', 'file');
        $result = [
            'available' => false,
            'driver'    => $driver,
            'latency_ms' => null,
            'error'     => null,
        ];

        try {
            $start = microtime(true);

            match ($driver) {
                'database' => self::checkDatabase(),
                'redis'    => self::checkRedis(),
                'memcached' => self::checkMemcached(),
                default    => self::checkFile(),
            };

            $result['latency_ms'] = round((microtime(true) - $start) * 1000, 2);
            $result['available'] = true;
        } catch (\Throwable $e) {
            $result['error'] = $e->getMessage();
        }

        return $result;
    }

    private static function checkFile(): void
    {
        Cache::put('cache_health_check', 'ok', 10);
        $value = Cache::get('cache_health_check');
        if ($value !== 'ok') {
            throw new \RuntimeException('File cache read-back mismatch');
        }
    }

    private static function checkDatabase(): void
    {
        $connection = Config::get('cache.stores.database.connection', 'sqlite');
        DB::connection($connection)->getPdo();
        Cache::put('cache_health_check', 'ok', 10);
        $value = Cache::get('cache_health_check');
        if ($value !== 'ok') {
            throw new \RuntimeException('Database cache read-back mismatch');
        }
    }

    private static function checkRedis(): void
    {
        Redis::connection()->ping();
        Cache::put('cache_health_check', 'ok', 10);
        $value = Cache::get('cache_health_check');
        if ($value !== 'ok') {
            throw new \RuntimeException('Redis cache read-back mismatch');
        }
    }

    private static function checkMemcached(): void
    {
        Cache::put('cache_health_check', 'ok', 10);
        $value = Cache::get('cache_health_check');
        if ($value !== 'ok') {
            throw new \RuntimeException('Memcached cache read-back mismatch');
        }
    }
}
