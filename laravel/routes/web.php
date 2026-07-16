<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\NotificationPreferenceController;

Route::get('/', function () {
    return view('welcome');
});

Route::middleware('auth')->group(function () {
    Route::get('/notifications/preferences', [NotificationPreferenceController::class, 'index']);
    Route::put('/notifications/preferences/{id}', [NotificationPreferenceController::class, 'update']);
    Route::post('/notifications/preferences/bulk', [NotificationPreferenceController::class, 'bulkUpdate']);
});
