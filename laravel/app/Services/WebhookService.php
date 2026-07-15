<?php

namespace App\Services;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Config;
use Illuminate\Support\Facades\Log;

class WebhookService
{
    /**
     * Verify the webhook signature for a given provider.
     */
    public function verifySignature(Request $request, string $provider): bool
    {
        $secret = Config::get("webhooks.providers.{$provider}.secret");

        if (!$secret) {
            Log::warning("No webhook secret configured for provider: {$provider}");
            return false;
        }

        $signature = $request->header('X-Webhook-Signature');
        if (!$signature) {
            return false;
        }

        $payload = $request->getContent();
        $expected = hash_hmac('sha256', $payload, $secret);

        return hash_equals($expected, $signature);
    }

    /**
     * Dispatch webhook payload to the appropriate handler and queue for retry on failure.
     */
    public function dispatch(string $provider, array $payload): void
    {
        $handlerClass = Config::get("webhooks.providers.{$provider}.handler");

        if (!$handlerClass || !class_exists($handlerClass)) {
            Log::warning("No handler configured for webhook provider: {$provider}");
            return;
        }

        try {
            app($handlerClass)->handle($payload);
        } catch (\Throwable $e) {
            Log::error("Webhook handler failed for {$provider}", [
                'error' => $e->getMessage(),
                'payload' => $payload,
            ]);

            // Queue for retry
            dispatch(function () use ($handlerClass, $payload, $provider) {
                $attempt = 0;
                $maxAttempts = Config::get('webhooks.retry.max_attempts', 3);

                while ($attempt < $maxAttempts) {
                    try {
                        app($handlerClass)->handle($payload);
                        return;
                    } catch (\Throwable $e) {
                        $attempt++;
                        $delay = Config::get('webhooks.retry.backoff_base', 60) * (2 ** ($attempt - 1));
                        sleep(min($delay, 3600));
                    }
                }

                Log::error("Webhook retry exhausted for {$provider}");
            });
        }
    }
}
