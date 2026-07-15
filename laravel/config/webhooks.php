<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Webhook Providers
    |--------------------------------------------------------------------------
    */
    'providers' => [
        // Example: 'stripe' => ['secret' => env('STRIPE_WEBHOOK_SECRET'), 'handler' => \App\Handlers\StripeWebhookHandler::class],
    ],

    /*
    |--------------------------------------------------------------------------
    | Retry Configuration
    |--------------------------------------------------------------------------
    */
    'retry' => [
        'max_attempts' => 3,
        'backoff_base' => 60, // seconds
    ],

];
