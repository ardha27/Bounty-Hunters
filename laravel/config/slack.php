<?php

return [
    'webhook_url' => env('SLACK_WEBHOOK_URL'),
    'default_channel' => env('SLACK_DEFAULT_CHANNEL', '#general'),
    'retry' => [
        'max_attempts' => 3,
        'timeout' => 5,
    ],
];
