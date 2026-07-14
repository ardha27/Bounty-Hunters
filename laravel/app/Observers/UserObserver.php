<?php

namespace App\Observers;

use App\Models\User;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class UserObserver
{
    /**
     * Handle the User "creating" event.
     */
    public function creating(User $user): void
    {
        if (empty($user->uuid)) {
            $user->uuid = (string) Str::uuid();
        }
        Log::info('User creating', ['email' => $user->email]);
    }

    /**
     * Handle the User "created" event.
     */
    public function created(User $user): void
    {
        Log::info('User created', ['id' => $user->id, 'email' => $user->email]);
    }

    /**
     * Handle the User "deleting" event.
     */
    public function deleting(User $user): void
    {
        Log::info('User deleting', ['id' => $user->id, 'email' => $user->email]);
    }

    /**
     * Handle the User "deleted" event.
     */
    public function deleted(User $user): void
    {
        Log::info('User deleted', ['id' => $user->id, 'email' => $user->email]);
    }
}
