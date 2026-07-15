<?php

namespace App\Listeners;

use Illuminate\Queue\Events\JobFailed;
use Illuminate\Support\Facades\Log;

class FailedJobListener
{
    /**
     * Handle the event.
     */
    public function handle(JobFailed $event): void
    {
        Log::channel('failed_jobs')->warning('Job failed', [
            'connection' => $event->connectionName,
            'job' => $event->job->resolveName(),
            'payload' => $event->job->payload(),
            'exception' => $event->exception->getMessage(),
            'trace' => $event->exception->getTraceAsString(),
            'timestamp' => now()->toIso8601String(),
        ]);
    }
}
