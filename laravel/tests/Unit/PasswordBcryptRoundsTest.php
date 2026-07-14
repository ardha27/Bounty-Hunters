<?php

namespace Tests\Unit;

use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class PasswordBcryptRoundsTest extends TestCase
{
    public function test_password_hash_respects_configured_rounds(): void
    {
        config(['hashing.bcrypt.rounds' => 12]);

        $user = new User();
        $user->password = 'test-password';

        $hashed = $user->password;
        $info = password_get_info($hashed);
        $this->assertEquals('bcrypt', $info['algoName'] ?? $info['algo']);
        $this->assertEquals(12, $info['options']['cost']);

        $this->assertTrue(Hash::check('test-password', $hashed));
    }

    public function test_old_password_still_verifies_with_default_rounds(): void
    {
        $oldHash = Hash::make('legacy-password', ['rounds' => 10]);

        $this->assertTrue(Hash::check('legacy-password', $oldHash));
    }
}
