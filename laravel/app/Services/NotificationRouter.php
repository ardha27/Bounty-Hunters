<?php

namespace App\Services;

use App\Models\NotificationPreference;

class NotificationRouter
{
    /**
     * Determine which channels a user should receive a notification on.
     */
    public function getEnabledChannels(int $userId, string $eventType): array
    {
        return NotificationPreference::where('user_id', $userId)
            ->where('event_type', $eventType)
            ->where('enabled', true)
            ->pluck('channel')
            ->toArray();
    }

    /**
     * Seed default preferences for a newly created user.
     */
    public function seedDefaults(int $userId): void
    {
        $defaults = [
            ['channel' => 'mail', 'event_type' => 'account'],
            ['channel' => 'mail', 'event_type' => 'security'],
            ['channel' => 'database', 'event_type' => 'account'],
            ['channel' => 'database', 'event_type' => 'security'],
        ];

        foreach ($defaults as $default) {
            NotificationPreference::firstOrCreate([
                'user_id' => $userId,
                'channel' => $default['channel'],
                'event_type' => $default['event_type'],
            ], [
                'enabled' => true,
            ]);
        }
    }
}
