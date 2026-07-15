<?php

namespace App\Observers;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class UserObserver
{
    /**
     * Handle the Model "creating" event.
     */
    public function creating(Model $model): void
    {
        if (method_exists($model, 'getKeyName') && $model->getKeyType() === 'string') {
            $model->{$model->getKeyName()} = (string) Str::uuid();
        }
    }

    /**
     * Handle the Model "retrieved" event — prevent lazy loading.
     */
    public function retrieved(Model $model): void
    {
        // n/a — lazy loading prevention handled via AppServiceProvider
    }
}
