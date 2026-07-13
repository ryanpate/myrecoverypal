# Video Posts in the Social Feed — Design

**Date:** 2026-07-13
**Status:** Approved approach; pending spec review

## Goal

Let users attach a short video to a social feed post, the same way they attach an image today.

## Constraints

- **Limits:** max 60 seconds duration, max 50MB file size (Cloudinary free-tier credit burn is the driver).
- **One media per post:** image OR video, never both.
- **Must work in the iOS Capacitor WebView** (`playsinline`, `accept="video/*"` file input).
- Scope is the social feed only — group posts are unchanged.

## Approach (chosen: upload through Django, like images)

The video uploads via the existing AJAX post form to `create_social_post`, is stored by the Cloudinary storage backend (video resource type), and renders as a native `<video>` player in the feed. Direct-to-Cloudinary signed upload was considered and rejected for now (more moving parts, unnecessary at current scale); migrating later doesn't change the data model. Gunicorn already runs `--timeout 120` and Django streams large multipart uploads to temp disk, so a 50MB upload through Railway works.

## Changes

### Model (`apps/accounts/models.py` + migration)

```python
video = models.FileField(upload_to='social_posts/videos/', blank=True, null=True)
```

When Cloudinary is enabled, the field uses `cloudinary_storage.storage.VideoMediaCloudinaryStorage` so the file is uploaded with `resource_type='video'` (required — the default image storage rejects videos). Locally it falls back to default file storage.

### Validation (`apps/accounts/image_utils.py` or sibling `video_utils.py`)

New `validate_video(video_file)` returning `(is_valid, error)`:
- extension/MIME whitelist: mp4, mov (quicktime), webm
- size ≤ 50MB

Duration is enforced client-side only (reading duration server-side needs ffmpeg; the 50MB cap bounds the damage if a client bypasses the JS check).

### View (`apps/accounts/views.py::create_social_post`)

- Read `request.FILES.get('video')`.
- Reject when both `image` and `video` are present (400).
- Validate video; create post with `video=video`.
- Add `video_url` to the JSON response.
- `social_feed_posts_api` adds `'video_url': post.video.url if post.video else None` to each serialized post.

### Composer UI (`social_feed.html`)

- Video button next to the existing image button; hidden `<input type="file" name="video" accept="video/*">`.
- On select, JS loads metadata into a detached `<video>` element to check duration ≤ 60s; rejects with a visible error otherwise.
- Inline preview (muted `<video>`) with the same remove button pattern as images; selecting a video clears any selected image and vice versa.
- Submit button enabled when content, image, or video present.
- Upload progress feedback (disable button + "Uploading…" state); 50MB takes seconds-to-a-minute, unlike images.

### Rendering

Anywhere `post.image` renders, add the video branch:

```html
{% if post.video %}<video controls preload="metadata" playsinline class="post-image" src="{{ post.video.url }}"></video>{% endif %}
```

Files: `social_feed.html`, `social_feed_fragment.html`, `dashboard.html`, plus the JS template used by the infinite-scroll feed API (`video_url`).

## Error handling

- Server validation errors return the existing `{'error': ...}` JSON shape and surface in the composer's error display.
- Upload failure (network) re-enables the form with an error message.

## Testing

View tests (same style as existing post tests):
- post with valid small video → 201/success, `video_url` in response
- oversized video → 400
- disallowed type (e.g., .avi) → 400
- image + video together → 400
- feed API includes `video_url`

## Out of scope

- Group post videos, video transcoding/thumbnails, server-side duration enforcement, direct-to-Cloudinary uploads.
