<?php

namespace App\Http\Controllers;

use App\Services\WebhookService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

class WebhookController extends Controller
{
    public function __construct(
        private readonly WebhookService $webhookService,
    ) {}

    /**
     * Handle incoming webhook with signature verification.
     */
    public function handle(Request $request, string $provider): JsonResponse
    {
        if (!$this->webhookService->verifySignature($request, $provider)) {
            return response()->json(['error' => 'Invalid signature'], 401);
        }

        $this->webhookService->dispatch($provider, $request->all());

        return response()->json(['status' => 'accepted']);
    }
}
