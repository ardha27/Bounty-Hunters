<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

Artisan::command('logs:clear {--days=7 : Delete logs older than this many days}', function () {
    $days = (int) $this->option('days');
    $cutoff = now()->subDays($days);
    $logPath = storage_path('logs');
    $deletedFiles = 0;
    $freedBytes = 0;

    if (!File::exists($logPath)) {
        $this->info('No logs directory found.');
        return;
    }

    $files = File::files($logPath);
    foreach ($files as $file) {
        if ($file->getExtension() !== 'log') {
            continue;
        }
        $modified = \Carbon\Carbon::createFromTimestamp($file->getMTime());
        if ($modified->lt($cutoff)) {
            $freedBytes += $file->getSize();
            File::delete($file->getPathname());
            $deletedFiles++;
        }
    }

    $freedFormatted = match (true) {
        $freedBytes >= 1_048_576 => number_format($freedBytes / 1_048_576, 2) . ' MB',
        $freedBytes >= 1_024 => number_format($freedBytes / 1_024, 2) . ' KB',
        default => $freedBytes . ' bytes',
    };

    $this->info("Deleted {$deletedFiles} file(s), freed {$freedFormatted}.");
})->purpose('Clear log files older than a given number of days');

Schedule::command('logs:clear')->dailyAt('00:00');
