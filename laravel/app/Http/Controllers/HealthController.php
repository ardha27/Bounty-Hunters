<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class HealthController
{
    /**
     * Database health check with retry logic.
     *
     * Performs a lightweight query (SELECT 1) to verify database connectivity.
     * Retries up to 3 times with exponential backoff on failure.
     */
    public function database(): JsonResponse
    {
        $maxRetries = 3;
        $attempt = 0;

        while ($attempt < $maxRetries) {
            try {
                $start = microtime(true);
                DB::select('SELECT 1');
                $latency = round((microtime(true) - $start) * 1000, 2);

                return response()->json([
                    'status' => 'healthy',
                    'service' => 'database',
                    'latency_ms' => $latency,
                    'timestamp' => now()->toIso8601String(),
                ]);
            } catch (\Throwable $e) {
                $attempt++;
                Log::warning("DB health check attempt {$attempt} failed", ['error' => $e->getMessage()]);

                if ($attempt >= $maxRetries) {
                    return response()->json([
                        'status' => 'unhealthy',
                        'service' => 'database',
                        'error' => $e->getMessage(),
                        'timestamp' => now()->toIso8601String(),
                    ], 503);
                }

                usleep((2 ** ($attempt - 1)) * 100_000); // 100ms, 200ms, 400ms
            }
        }

        return response()->json([
            'status' => 'unknown',
            'service' => 'database',
            'timestamp' => now()->toIso8601String(),
        ], 500);
    }
}
