<?php

namespace App\Http\Controllers;

use App\Models\NotificationPreference;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class NotificationPreferenceController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $preferences = NotificationPreference::where('user_id', $request->user()->id)->get();
        return response()->json($preferences);
    }

    public function update(Request $request, int $id): JsonResponse
    {
        $preference = NotificationPreference::where('user_id', $request->user()->id)
            ->findOrFail($id);

        $validated = $request->validate([
            'enabled' => 'required|boolean',
        ]);

        $preference->update($validated);
        return response()->json($preference);
    }

    public function bulkUpdate(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'preferences' => 'required|array',
            'preferences.*.id' => 'required|integer',
            'preferences.*.enabled' => 'required|boolean',
        ]);

        $ids = array_column($validated['preferences'], 'id');
        $preferences = NotificationPreference::where('user_id', $request->user()->id)
            ->whereIn('id', $ids)
            ->get()
            ->keyBy('id');

        foreach ($validated['preferences'] as $pref) {
            if (isset($preferences[$pref['id']])) {
                $preferences[$pref['id']]->update(['enabled' => $pref['enabled']]);
            }
        }

        return response()->json(['updated' => count($validated['preferences'])]);
    }
}
