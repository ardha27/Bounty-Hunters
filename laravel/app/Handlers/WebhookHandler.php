<?php

namespace App\Handlers;

use Illuminate\Support\Facades\Log;

interface WebhookHandler
{
    public function handle(array $payload): void;
}
