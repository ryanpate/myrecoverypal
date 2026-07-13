# Video Posts in the Social Feed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users attach a short video (≤60s, ≤50MB) to a social feed post, stored on Cloudinary, rendered as a native `<video>` player.

**Architecture:** A new `video` FileField on `SocialPost` using Cloudinary's video storage backend (videos MUST use `resource_type='video'`; the default image storage rejects them). Upload goes through the existing AJAX `create_social_post` view. Server validates type/size; client-side JS enforces the 60s duration cap. One media per post: image OR video.

**Tech Stack:** Django 5.0.10, django-cloudinary-storage (`VideoMediaCloudinaryStorage`), vanilla JS in `social_feed.html`.

**Spec:** `docs/superpowers/specs/2026-07-13-video-posts-design.md`

## Global Constraints

- Max video size: **50MB** (server-enforced). Max duration: **60 seconds** (client-enforced only — no ffmpeg server-side).
- Allowed types: **mp4, mov (video/quicktime), webm**.
- A post may have an image OR a video, never both (server-enforced, 400).
- `<video>` tags must include `playsinline` (iOS Capacitor WebView) and `preload="metadata"`.
- Scope: social feed only. Group posts unchanged. Dashboard/fragment templates get *rendering* only, no composer changes.
- Test command: `python3 manage.py test apps.accounts.test_video_posts -v 2` (run from repo root).
- Match existing code style; do not reformat adjacent code.

---

### Task 1: Server-side video validation helper

**Files:**
- Modify: `apps/accounts/image_utils.py` (add constants + `validate_video` at the end of the file)
- Test: `apps/accounts/test_video_posts.py` (new file)

**Interfaces:**
- Produces: `validate_video(video_file) -> (bool, str|None)` — same shape as the existing `validate_image`. Task 3 imports it in the view.

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_video_posts.py`:

```python
"""Tests for video posts in the social feed."""
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import SocialPost

User = get_user_model()


def small_mp4(name='clip.mp4', content_type='video/mp4', size=1024):
    return SimpleUploadedFile(name, b'\x00' * size, content_type=content_type)


class FakeFile:
    """Stub with just the attributes validate_video reads (avoids allocating 50MB)."""
    def __init__(self, name='clip.mp4', size=1024, content_type='video/mp4'):
        self.name = name
        self.size = size
        self.content_type = content_type


class ValidateVideoTests(TestCase):
    def test_valid_mp4(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(FakeFile())
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_valid_mov_and_webm(self):
        from apps.accounts.image_utils import validate_video
        self.assertTrue(validate_video(FakeFile('a.mov', content_type='video/quicktime'))[0])
        self.assertTrue(validate_video(FakeFile('a.webm', content_type='video/webm'))[0])

    def test_oversized_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(FakeFile(size=51 * 1024 * 1024))
        self.assertFalse(is_valid)
        self.assertIn('50MB', error)

    def test_disallowed_type_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(
            FakeFile('a.avi', content_type='video/x-msvideo'))
        self.assertFalse(is_valid)

    def test_no_file_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(None)
        self.assertFalse(is_valid)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.test_video_posts.ValidateVideoTests -v 2`
Expected: FAIL/ERROR with `ImportError: cannot import name 'validate_video'`

- [ ] **Step 3: Implement `validate_video`**

Append to `apps/accounts/image_utils.py` (constants near the existing `ALLOWED_IMAGE_TYPES` block at the top, function at the end of the file):

```python
# Video upload limits (social feed video posts)
MAX_VIDEO_SIZE_MB = 50
ALLOWED_VIDEO_TYPES = {
    'video/mp4': '.mp4',
    'video/quicktime': '.mov',
    'video/webm': '.webm',
}
```

```python
def validate_video(video_file):
    """
    Validate an uploaded video file (type + size only — duration is
    enforced client-side; the size cap bounds a bypassed duration check).

    Args:
        video_file: Django UploadedFile object

    Returns:
        tuple: (is_valid, error_message)
    """
    if not video_file:
        return False, "No video file provided"

    max_size = MAX_VIDEO_SIZE_MB * 1024 * 1024
    if video_file.size > max_size:
        return False, f"Video size exceeds {MAX_VIDEO_SIZE_MB}MB limit"

    content_type = getattr(video_file, 'content_type', None)
    ext = os.path.splitext(video_file.name)[1].lower()
    if content_type not in ALLOWED_VIDEO_TYPES and ext not in ALLOWED_VIDEO_TYPES.values():
        return False, "Video must be an MP4, MOV, or WebM file"

    return True, None
```

(`os` is already imported at the top of `image_utils.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.test_video_posts.ValidateVideoTests -v 2`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/image_utils.py apps/accounts/test_video_posts.py
git commit -m "feat(feed): validate_video helper for video post uploads"
```

---

### Task 2: `video` field on SocialPost + migration

**Files:**
- Modify: `apps/accounts/models.py` (storage selector above `class SocialPost` at ~line 1854; field next to `image` at line 1864)
- Create: `apps/accounts/migrations/0065_socialpost_video.py` (via makemigrations)
- Test: `apps/accounts/test_video_posts.py` (append)

**Interfaces:**
- Consumes: `is_cloudinary_enabled()` from `apps/accounts/image_utils.py`.
- Produces: `SocialPost.video` — FileField, `blank=True, null=True`, `upload_to='social_posts/videos/'`. Tasks 3–5 read `post.video` / `post.video.url`.

- [ ] **Step 1: Write the failing test**

Append to `apps/accounts/test_video_posts.py`:

```python
class SocialPostVideoFieldTests(TestCase):
    def test_post_accepts_video_file(self):
        user = User.objects.create_user(username='vid', password='x')
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            post = SocialPost.objects.create(
                author=user, content='clip', video=small_mp4())
            self.assertTrue(post.video.name.startswith('social_posts/videos/'))
            self.assertTrue(post.video.url)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.accounts.test_video_posts.SocialPostVideoFieldTests -v 2`
Expected: FAIL with `TypeError: SocialPost() got unexpected keyword arguments: 'video'`

- [ ] **Step 3: Add the storage selector and field**

In `apps/accounts/models.py`, directly above `class SocialPost(models.Model):`:

```python
def _social_post_video_storage():
    """Videos must upload to Cloudinary with resource_type='video' — the
    default MediaCloudinaryStorage uploads as an image resource and
    rejects video files. Falls back to default storage locally."""
    from apps.accounts.image_utils import is_cloudinary_enabled
    if is_cloudinary_enabled():
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    from django.core.files.storage import default_storage
    return default_storage
```

In `SocialPost`, directly after the `image` field (line 1864):

```python
    video = models.FileField(
        upload_to='social_posts/videos/', blank=True, null=True,
        storage=_social_post_video_storage)
```

(Passing the *callable* — not calling it — keeps the storage choice out of the migration and lets it differ between local and production.)

- [ ] **Step 4: Generate and run the migration**

Run: `python3 manage.py makemigrations accounts -n socialpost_video`
Expected: creates `apps/accounts/migrations/0065_socialpost_video.py` adding one field.

Run: `python3 manage.py migrate accounts`
Expected: `Applying accounts.0065_socialpost_video... OK`

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 manage.py test apps.accounts.test_video_posts.SocialPostVideoFieldTests -v 2`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/0065_socialpost_video.py apps/accounts/test_video_posts.py
git commit -m "feat(feed): SocialPost.video field with Cloudinary video storage"
```

---

### Task 3: Accept video in `create_social_post` + expose `video_url` in feed API

**Files:**
- Modify: `apps/accounts/views.py::create_social_post` (~line 4436) and `apps/accounts/views.py::social_feed_posts_api` (serialization dict at ~line 4403, the line `'image_url': post.image.url if post.image else None,`)
- Test: `apps/accounts/test_video_posts.py` (append)

**Interfaces:**
- Consumes: `validate_video` (Task 1), `SocialPost.video` (Task 2).
- Produces: `create_social_post` accepts multipart field `video`; success JSON gains `'video_url'`; error JSONs use the existing `{'error': str}` shape with status 400. Feed API posts gain `'video_url'`. Task 5's JS relies on the field name `video`.

- [ ] **Step 1: Write the failing tests**

Append to `apps/accounts/test_video_posts.py`:

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CreateVideoPostViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='poster', password='x')
        self.client.force_login(self.user)
        self.url = reverse('accounts:create_social_post')

    def test_create_post_with_video(self):
        resp = self.client.post(self.url, {'content': 'my clip', 'video': small_mp4()})
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['post']['video_url'])
        post = SocialPost.objects.get(author=self.user)
        self.assertTrue(post.video)

    def test_video_only_post_allowed(self):
        resp = self.client.post(self.url, {'video': small_mp4()})
        self.assertTrue(resp.json()['success'])

    def test_oversized_video_rejected(self):
        big = small_mp4(size=51 * 1024 * 1024)
        resp = self.client.post(self.url, {'content': 'x', 'video': big})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SocialPost.objects.count(), 0)

    def test_bad_video_type_rejected(self):
        bad = small_mp4(name='clip.avi', content_type='video/x-msvideo')
        resp = self.client.post(self.url, {'content': 'x', 'video': bad})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SocialPost.objects.count(), 0)

    def test_image_and_video_together_rejected(self):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (10, 10)).save(buf, format='JPEG')
        img = SimpleUploadedFile('a.jpg', buf.getvalue(), content_type='image/jpeg')
        resp = self.client.post(
            self.url, {'content': 'x', 'image': img, 'video': small_mp4()})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('not both', resp.json()['error'])

    def test_feed_api_includes_video_url(self):
        SocialPost.objects.create(author=self.user, content='clip', video=small_mp4())
        resp = self.client.get(reverse('accounts:social_feed_posts_api'))
        posts = resp.json()['posts']
        self.assertTrue(posts[0]['video_url'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.test_video_posts.CreateVideoPostViewTests -v 2`
Expected: `test_create_post_with_video` fails with `KeyError: 'video_url'`; `test_video_only_post_allowed` fails with 400 ("must have either text or an image"); the rejection tests fail because the post is created (no 400).

- [ ] **Step 3: Modify `create_social_post`**

In `apps/accounts/views.py`, update the top of `create_social_post`:

```python
    from .image_utils import validate_image, compress_image, is_cloudinary_enabled, validate_video

    content = request.POST.get('content', '').strip()
    visibility = request.POST.get('visibility', 'public')
    image = request.FILES.get('image')
    video = request.FILES.get('video')

    # Require either content or media
    if not content and not image and not video:
        return JsonResponse({'error': 'Post must have text, an image, or a video'}, status=400)

    # One media per post
    if image and video:
        return JsonResponse({'error': 'A post can have an image or a video, not both'}, status=400)

    # Process image if provided
    if image:
        is_valid, error = validate_image(image)
        if not is_valid:
            return JsonResponse({'error': error}, status=400)

        # Compress for local storage (Cloudinary handles optimization automatically)
        if not is_cloudinary_enabled():
            image = compress_image(image, max_dimension=1920)

    # Validate video if provided (duration is capped client-side; size here)
    if video:
        is_valid, error = validate_video(video)
        if not is_valid:
            return JsonResponse({'error': error}, status=400)
```

In the `SocialPost.objects.create(...)` call add `video=video,` after `image=image`. In the success JSON's `'post'` dict, after the `'image_url'` line add:

```python
                'video_url': post.video.url if post.video else None,
```

- [ ] **Step 4: Add `video_url` to `social_feed_posts_api`**

In the `posts_data.append({...})` dict, directly after the `'image_url'` line:

```python
                'video_url': post.video.url if post.video else None,
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.test_video_posts -v 2`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/accounts/test_video_posts.py
git commit -m "feat(feed): accept video uploads in create_social_post + feed API video_url"
```

---

### Task 4: Render videos in feed templates

**Files:**
- Modify: `apps/accounts/templates/accounts/social_feed.html:1736-1738`
- Modify: `apps/accounts/templates/accounts/social_feed_fragment.html:247-249`
- Modify: `apps/accounts/templates/accounts/dashboard.html:1159-1161`
- Test: `apps/accounts/test_video_posts.py` (append)

**Interfaces:**
- Consumes: `post.video` (Task 2).
- Produces: `<video>` element with class `post-image` (reuses existing sizing CSS; `mobile-post-image` on dashboard).

- [ ] **Step 1: Write the failing test**

Append to `apps/accounts/test_video_posts.py`:

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FeedVideoRenderTests(TestCase):
    def test_feed_renders_video_player(self):
        user = User.objects.create_user(username='render', password='x')
        SocialPost.objects.create(author=user, content='clip', video=small_mp4())
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertContains(resp, '<video')
        self.assertContains(resp, 'playsinline')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.accounts.test_video_posts.FeedVideoRenderTests -v 2`
Expected: FAIL — response contains no `<video` for the post

- [ ] **Step 3: Add the video branch to all three templates**

`social_feed.html` — the block at line 1736 currently reads:

```html
                {% if post.image %}
                <img src="{{ post.image.url }}" alt="Image shared by {{ post.author.username }} in recovery community" class="post-image" loading="lazy">
                {% endif %}
```

Change to:

```html
                {% if post.image %}
                <img src="{{ post.image.url }}" alt="Image shared by {{ post.author.username }} in recovery community" class="post-image" loading="lazy">
                {% elif post.video %}
                <video src="{{ post.video.url }}" class="post-image" controls preload="metadata" playsinline></video>
                {% endif %}
```

`social_feed_fragment.html` line 247 — same pattern:

```html
                {% if post.image %}
                <img src="{{ post.image.url }}" alt="Post image" class="post-image" loading="lazy">
                {% elif post.video %}
                <video src="{{ post.video.url }}" class="post-image" controls preload="metadata" playsinline></video>
                {% endif %}
```

`dashboard.html` line 1159 — same pattern with the dashboard's class:

```html
                        {% if post.image %}
                        <img src="{{ post.image.url }}" alt="Image shared by {{ post.author.username }} in recovery community" class="mobile-post-image">
                        {% elif post.video %}
                        <video src="{{ post.video.url }}" class="mobile-post-image" controls preload="metadata" playsinline></video>
                        {% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.accounts.test_video_posts -v 2`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/templates/accounts/social_feed.html apps/accounts/templates/accounts/social_feed_fragment.html apps/accounts/templates/accounts/dashboard.html apps/accounts/test_video_posts.py
git commit -m "feat(feed): render video posts as native players in feed templates"
```

---

### Task 5: Composer UI — video button, duration check, preview

**Files:**
- Modify: `apps/accounts/templates/accounts/social_feed.html` (form markup ~lines 1562-1585; JS ~lines 2040-2156)

**Interfaces:**
- Consumes: multipart field name `video` (Task 3). The form already submits via `new FormData(this)`, so a named file input is picked up automatically; the page reloads on success, so no client-side post rendering is needed.

No automated test for this task (vanilla JS in a Django template; the project has no JS test runner). Verification is manual — Step 4.

- [ ] **Step 1: Add video input, button, and preview markup**

After the image preview container (ends line 1570), add:

```html
                <!-- Video Preview -->
                <div id="video-preview-container" style="display: none; padding: 0.5rem; margin-top: 0.5rem;">
                    <div style="position: relative; display: inline-block; max-width: 100%;">
                        <video id="video-preview" muted playsinline style="max-width: 100%; max-height: 300px; border-radius: 8px;"></video>
                        <button type="button" id="remove-video-btn" style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
```

Inside the `post-actions` div, after the photo button (line 1577), add:

```html
                        <input type="file" name="video" id="post-video-input" accept="video/*" style="display: none;">
                        <button type="button" id="add-video-btn" class="action-btn" style="padding: 0.25rem 0.75rem; margin: 0;" title="Add video (max 60s)">
                            <i class="fas fa-video"></i>
                        </button>
```

- [ ] **Step 2: Add the video JS handlers**

After the `removeImageBtn` handler block (ends line 2106), add:

```javascript
    // Video upload handlers
    const addVideoBtn = document.getElementById('add-video-btn');
    const videoInput = document.getElementById('post-video-input');
    const videoPreviewContainer = document.getElementById('video-preview-container');
    const videoPreview = document.getElementById('video-preview');
    const removeVideoBtn = document.getElementById('remove-video-btn');

    function clearVideoSelection() {
        if (videoInput) videoInput.value = '';
        if (videoPreviewContainer) videoPreviewContainer.style.display = 'none';
        if (videoPreview) videoPreview.removeAttribute('src');
    }

    if (addVideoBtn && videoInput) {
        addVideoBtn.addEventListener('click', function() {
            videoInput.click();
        });

        videoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            if (!file.type.startsWith('video/')) {
                alert('Please select a video file');
                this.value = '';
                return;
            }

            if (file.size > 50 * 1024 * 1024) {
                alert('Video size must be less than 50MB');
                this.value = '';
                return;
            }

            // Check duration (max 60s) by loading metadata
            const input = this;
            const objectUrl = URL.createObjectURL(file);
            const probe = document.createElement('video');
            probe.preload = 'metadata';
            probe.onloadedmetadata = function() {
                URL.revokeObjectURL(objectUrl);
                if (probe.duration > 60) {
                    alert('Videos must be 60 seconds or less');
                    input.value = '';
                    return;
                }
                // Video replaces any selected image (one media per post)
                if (imageInput) imageInput.value = '';
                if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';
                if (imagePreview) imagePreview.src = '';

                if (videoPreview && videoPreviewContainer) {
                    videoPreview.src = URL.createObjectURL(file);
                    videoPreviewContainer.style.display = 'block';
                }
                if (submitBtn) submitBtn.disabled = false;
            };
            probe.onerror = function() {
                URL.revokeObjectURL(objectUrl);
                alert('Could not read that video file');
                input.value = '';
            };
            probe.src = objectUrl;
        });
    }

    if (removeVideoBtn) {
        removeVideoBtn.addEventListener('click', function() {
            clearVideoSelection();
            if (textarea && submitBtn) {
                const hasContent = textarea.value.trim().length > 0;
                const hasImage = imageInput && imageInput.files.length > 0;
                submitBtn.disabled = !hasContent && !hasImage;
            }
        });
    }
```

- [ ] **Step 3: Wire mutual exclusion + submit-state into the existing handlers**

Three edits to existing JS:

1. In the textarea `input` handler (line 2043), change:

```javascript
            const hasImage = document.getElementById('post-image-input').files.length > 0;
            submitBtn.disabled = length === 0 && !hasImage;
```

to:

```javascript
            const hasImage = document.getElementById('post-image-input').files.length > 0;
            const hasVideo = document.getElementById('post-video-input').files.length > 0;
            submitBtn.disabled = length === 0 && !hasImage && !hasVideo;
```

2. In the image `change` handler, right before the `// Show preview` comment (line 2078), add (image replaces any selected video):

```javascript
                clearVideoSelection();
```

3. In the `removeImageBtn` handler (line 2101-2103), change the disable check to also count a selected video:

```javascript
            if (textarea && submitBtn) {
                const hasContent = textarea.value.trim().length > 0;
                const hasVideo = videoInput && videoInput.files.length > 0;
                submitBtn.disabled = !hasContent && !hasVideo;
            }
```

4. In the form-submit success branch (after `if (imagePreview) imagePreview.src = '';`, line 2135), add:

```javascript
                    clearVideoSelection();
```

(`clearVideoSelection` is a hoisted function declaration in the same inline `<script>`, and the image handler only calls it at event time — ordering is safe.)

- [ ] **Step 4: Manual verification**

Run: `python3 manage.py runserver`, log in, open `/accounts/social-feed/` and verify:
- Video button opens a file picker filtered to videos.
- Selecting a >60s video shows the duration alert and clears the input.
- Selecting a valid short video shows an inline preview; the Post button enables.
- Selecting a video then an image (and vice versa) keeps only the latest selection's preview.
- Posting uploads (button shows spinner), page reloads, and the new post shows a playable `<video>` player.
- Remove (×) on the preview clears it and disables Post when the textarea is empty.

- [ ] **Step 5: Run the full new test module one last time**

Run: `python3 manage.py test apps.accounts.test_video_posts -v 2`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/templates/accounts/social_feed.html
git commit -m "feat(feed): video button in post composer with 60s duration check"
```

---

## Post-plan notes (not tasks)

- Production requires no new env vars — Cloudinary creds already configured; `VideoMediaCloudinaryStorage` uses them.
- Watch Cloudinary credit usage after launch (Media Library → Reports); the 50MB/60s caps are the cost control.
- Deferred (spec "Out of scope"): group post videos, thumbnails/transcoding, server-side duration enforcement, direct-to-Cloudinary signed uploads.
