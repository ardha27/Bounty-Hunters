<?php

namespace App\Listeners;

use Illuminate\Contracts\Queue\Job;
use Illuminate\Queue\Events\JobFailed;
use Illuminate\Support\Facades\Log;

class LogFailedJob
{
    /**
     * Handle the event.
     */
    public function handle(JobFailed $event): void
    {
        $exception = $event->exception;
        $job = $event->job;

        $logData = [
            'job_id' => $job->getJobId() ?? 'unknown',
            'queue' => $job->getQueue(),
            'name' => $job->payload()['displayName'] ?? 'unknown',
            'attempts' => $job->attempts(),
            'exception' => get_class($exception),
            'message' => $exception->getMessage(),
            'failed_at' => now()->toDateTimeString(),
        ];

        Log::channel('failed_jobs')->error('Job failed', $logData);
    }
}
