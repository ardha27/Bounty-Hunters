<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

Artisan::command('queue:failed-summary', function () {
    $failures = DB::table('failed_jobs')
        ->selectRaw("json_unquote(json_extract(payload, '$.displayName')) as job_name, count(*) as count")
        ->groupBy('job_name')
        ->orderByDesc('count')
        ->get();

    if ($failures->isEmpty()) {
        $this->info('No failed jobs.');
        return;
    }

    $this->table(
        ['Job', 'Count'],
        $failures->map(fn ($f) => [$f->job_name ?? 'unknown', $f->count])->toArray()
    );
})->purpose('Show summary of failed jobs grouped by type');
