<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class FailedJobSummary extends Command
{
    protected $signature = 'queue:failed-summary {--hours=24 : Hours to look back}';
    protected $description = 'Show a summary of recently failed jobs with counts';

    public function handle(): int
    {
        $hours = (int) $this->option('hours');
        $since = now()->subHours($hours);

        $failed = DB::table('failed_jobs')
            ->where('failed_at', '>=', $since)
            ->get();

        if ($failed->isEmpty()) {
            $this->info("No failed jobs in the last {$hours} hours.");
            return self::SUCCESS;
        }

        $byType = $failed->groupBy(function ($job) {
            $payload = json_decode($job->payload, true);
            return $payload['displayName'] ?? 'unknown';
        });

        $this->table(
            ['Job Type', 'Count', 'First Failed', 'Last Failed'],
            $byType->map(function ($jobs, $type) {
                return [
                    $type,
                    $jobs->count(),
                    $jobs->min('failed_at'),
                    $jobs->max('failed_at'),
                ];
            })->toArray()
        );

        return self::SUCCESS;
    }
}
