<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Route;
use Tests\TestCase;

class RouteTest extends TestCase
{
    public function test_all_get_routes_return_non_500(): void
    {
        $routes = Route::getRoutes();
        
        foreach ($routes as $route) {
            $methods = $route->methods();
            if (!in_array('GET', $methods)) {
                continue;
            }

            $uri = $route->uri();
            // Convert route params to dummy values
            $uri = preg_replace('/\{(\w+)\}/', '1', $uri);
            
            $response = $this->get($uri);
            $this->assertNotEquals(500, $response->status(), "Route $uri returned 500");
        }
    }
}
