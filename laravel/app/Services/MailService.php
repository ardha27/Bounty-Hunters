<?php

namespace App\Services;

use Illuminate\Mail\MailManager;
use Illuminate\Support\Facades\Config;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;

class MailService
{
    /**
     * Send mail with automatic SMTP fallback to log driver.
     */
    public static function send(\Closure $callback, ?string $mailer = null): void
    {
        $primaryMailer = $mailer ?? Config::get('mail.default', 'failover');

        try {
            Mail::mailer($primaryMailer)->send(
                new class($callback) {
                    public function __construct(private \Closure $callback) {}
                    public function build(): void
                    {
                        ($this->callback)($this);
                    }
                }
            );
        } catch (\Throwable $e) {
            $fallback = Config::get('mail.fallback', 'log');
            Log::warning("Mail failed via {$primaryMailer}, falling back to {$fallback}", [
                'error' => $e->getMessage(),
            ]);

            try {
                Mail::mailer($fallback)->send(
                    new class($callback) {
                        public function __construct(private \Closure $callback) {}
                        public function build(): void
                        {
                            ($this->callback)($this);
                        }
                    }
                );
            } catch (\Throwable $e2) {
                Log::error("Mail fallback also failed via {$fallback}", [
                    'error' => $e2->getMessage(),
                ]);
            }
        }
    }
}
