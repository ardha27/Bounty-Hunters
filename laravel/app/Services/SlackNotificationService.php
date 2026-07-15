<?php

namespace App\Services;

use Illuminate\Support\Facades\Config;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class SlackNotificationService
{
    private const TIMEOUT = 5;
    private const MAX_RETRIES = 3;

    /**
     * Send a notification to Slack with retry and timeout.
     */
    public function send(string $text, ?string $channel = null, ?string $webhookUrl = null): bool
    {
        $url = $webhookUrl ?? Config::get('slack.webhook_url');
        if (!$url) {
            Log::warning('Slack webhook URL not configured');
            return false;
        }

        $attempt = 0;

        while ($attempt < self::MAX_RETRIES) {
            try {
                $response = Http::timeout(self::TIMEOUT)
                    ->post($url, [
                        'text' => $text,
                        'channel' => $channel,
                    ]);

                if ($response->successful()) {
                    return true;
                }

                $attempt++;
                Log::warning("Slack notification attempt {$attempt} failed", [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);
            } catch (\Throwable $e) {
                $attempt++;
                Log::warning("Slack notification attempt {$attempt} error", [
                    'error' => $e->getMessage(),
                ]);
            }

            if ($attempt < self::MAX_RETRIES) {
                usleep((2 ** ($attempt - 1)) * 100_000);
            }
        }

        Log::error('Slack notification failed after all retries');
        return false;
    }
}
