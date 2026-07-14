<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

Artisan::command('logs:clear', function () {
    $days = (int) ($this->option('days') ?? 7);
    $logPath = storage_path('logs');
    $count = 0;
    $bytesFreed = 0;

    if (!is_dir($logPath)) {
        $this->info('No logs directory found.');
        return;
    }

    $cutoff = now()->subDays($days)->getTimestamp();

    foreach (glob($logPath . '/*.log') as $file) {
        if (filemtime($file) < $cutoff) {
            $bytesFreed += filesize($file);
            unlink($file);
            $count++;
        }
    }

    $this->info("Cleared {$count} log file(s), freed {$bytesFreed} bytes.");
})->purpose('Clear log files older than N days')
  ->option('days', null, true, 'Number of days', 7);

Schedule::command('logs:clear')->dailyAt('01:00');
