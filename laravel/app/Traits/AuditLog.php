<?php

namespace App\Traits;

use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;

trait AuditLog
{
    /**
     * Boot the trait — register model event listeners.
     */
    public static function bootAuditLog(): void
    {
        static::created(function ($model) {
            self::logChange($model, 'created');
        });

        static::updated(function ($model) {
            $changes = $model->getChanges();
            // Remove timestamps from tracked changes
            unset($changes['updated_at']);
            if (!empty($changes)) {
                self::logChange($model, 'updated', $changes);
            }
        });

        static::deleted(function ($model) {
            self::logChange($model, 'deleted');
        });
    }

    /**
     * Log an audit entry for the model change.
     */
    protected static function logChange($model, string $event, ?array $changes = null): void
    {
        $userId = Auth::id();

        Log::channel('audit')->info("Model {$event}", [
            'model' => get_class($model),
            'model_id' => $model->getKey(),
            'user_id' => $userId,
            'changes' => $changes,
            'timestamp' => now()->toIso8601String(),
        ]);
    }
}
