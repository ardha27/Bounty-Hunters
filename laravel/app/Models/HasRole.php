<?php

namespace App\Models;

use Illuminate\Support\Facades\DB;

trait HasRole
{
    /**
     * Check if the user has a given role.
     */
    public function hasRole(string $role): bool
    {
        $roleExists = DB::table('roles')->where('name', $role)->first();
        if (!$roleExists) {
            return false;
        }

        return DB::table('role_user')
            ->where('user_id', $this->getKey())
            ->where('role_id', $roleExists->id)
            ->exists();
    }

    /**
     * Assign a role to the user.
     */
    public function assignRole(string $role): void
    {
        $roleRecord = DB::table('roles')->where('name', $role)->first();
        if (!$roleRecord) {
            return;
        }

        DB::table('role_user')->insertOrIgnore([
            'user_id' => $this->getKey(),
            'role_id' => $roleRecord->id,
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }

    /**
     * Get all roles assigned to the user.
     *
     * @return array<string>
     */
    public function roles(): array
    {
        return DB::table('role_user')
            ->join('roles', 'roles.id', '=', 'role_user.role_id')
            ->where('role_user.user_id', $this->getKey())
            ->pluck('roles.name')
            ->toArray();
    }
}
