<?php

namespace App\Console\Commands;

use App\Services\CacheHealthCheck;
use Illuminate\Console\Command;

class CacheHealthCommand extends Command
{
    protected $signature = 'cache:health';
    protected $description = 'Check the health of the configured cache store';

    public function handle(): int
    {
        $result = CacheHealthCheck::check();

        if ($result['available']) {
            $this->info("Cache store [{$result['driver']}] is healthy.");
            $this->line("Latency: {$result['latency_ms']} ms");
            return self::SUCCESS;
        }

        $this->error("Cache store [{$result['driver']}] is unavailable: {$result['error']}");
        return self::FAILURE;
    }
}
