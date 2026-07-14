<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

class HealthController extends Controller
{
    /**
     * Check database connectivity and return health status.
     */
    public function database(): JsonResponse
    {
        $maxRetries = 3;
        $delayMs = 500;

        for ($attempt = 1; $attempt <= $maxRetries; $attempt++) {
            try {
                $start = microtime(true);
                DB::connection()->getPdo();
                $latency = round((microtime(true) - $start) * 1000, 2);

                return response()->json([
                    'status' => 'healthy',
                    'driver' => DB::connection()->getDriverName(),
                    'latency_ms' => $latency,
                    'connection_name' => DB::connection()->getName(),
                ]);
            } catch (\Exception $e) {
                if ($attempt >= $maxRetries) {
                    return response()->json([
                        'status' => 'unhealthy',
                        'error' => $e->getMessage(),
                    ], 503);
                }
                usleep($delayMs * 1000);
            }
        }

        return response()->json([
            'status' => 'unhealthy',
            'error' => 'Max retry attempts exceeded',
        ], 503);
    }
}
