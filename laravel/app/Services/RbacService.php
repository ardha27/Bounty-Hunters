<?php

namespace App\Services;

use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Gate;

class RbacService
{
    /** @var array<string, array<string, bool>> */
    private static array $permissions = [];

    /**
     * Define roles and their permissions.
     *
     * @param array<string, array<string>> $roles  ['role' => ['action1', 'action2']]
     */
    public static function define(array $roles): void
    {
        foreach ($roles as $role => $actions) {
            foreach ($actions as $action) {
                self::$permissions[$role][$action] = true;
            }

            Gate::define($role, function ($user) use ($role) {
                return $user->hasRole($role);
            });
        }
    }

    /**
     * Check if a role has a specific permission.
     */
    public static function can(string $role, string $action): bool
    {
        return Arr::get(self::$permissions, "{$role}.{$action}", false);
    }

    /**
     * Get all permissions for a role.
     *
     * @return array<string>
     */
    public static function permissions(string $role): array
    {
        return array_keys(self::$permissions[$role] ?? []);
    }
}
