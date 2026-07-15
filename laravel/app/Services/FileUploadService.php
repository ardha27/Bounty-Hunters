<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class FileUploadService
{
    private const DEDUP_EXPIRY = 86400; // 24 hours

    /**
     * Upload a file with checksum dedup and optional thumbnail generation.
     *
     * @return array{path: string, url: string, checksum: string}
     */
    public function upload(UploadedFile $file, string $directory = 'uploads'): array
    {
        $checksum = md5_file($file->getRealPath());
        $ext = $file->getClientOriginalExtension();
        $filename = $checksum . ($ext ? '.' . $ext : '');

        $path = "{$directory}/{$filename}";

        // Checksum dedup — skip upload if file already exists
        if (!Storage::disk('public')->exists($path)) {
            Storage::disk('public')->putFileAs($directory, $file, $filename);
        }

        // Generate thumbnail for images
        if (in_array(strtolower($ext), ['jpg', 'jpeg', 'png', 'gif', 'webp'])) {
            $this->generateThumbnail($file, $directory, $checksum);
        }

        return [
            'path' => $path,
            'url' => Storage::disk('public')->url($path),
            'checksum' => $checksum,
        ];
    }

    /**
     * Generate a thumbnail for an image file.
     */
    private function generateThumbnail(UploadedFile $file, string $directory, string $checksum): void
    {
        try {
            $image = match (strtolower($file->getClientOriginalExtension())) {
                'jpg', 'jpeg' => imagecreatefromjpeg($file->getRealPath()),
                'png' => imagecreatefrompng($file->getRealPath()),
                'gif' => imagecreatefromgif($file->getRealPath()),
                'webp' => imagecreatefromwebp($file->getRealPath()),
                default => null,
            };

            if (!$image) {
                return;
            }

            $origW = imagesx($image);
            $origH = imagesy($image);
            $thumbW = 200;
            $thumbH = (int) round($origH * ($thumbW / max($origW, 1)));

            $thumb = imagecreatetruecolor($thumbW, $thumbH);
            imagecopyresampled($thumb, $image, 0, 0, 0, 0, $thumbW, $thumbH, $origW, $origH);

            $thumbPath = storage_path("app/public/{$directory}/{$checksum}_thumb.jpg");
            imagejpeg($thumb, $thumbPath, 80);

            imagedestroy($image);
            imagedestroy($thumb);
        } catch (\Throwable $e) {
            Log::warning("Thumbnail generation failed", ['error' => $e->getMessage()]);
        }
    }
}
