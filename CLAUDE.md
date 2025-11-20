# CLAUDE.md - MyRecoveryPal Development Guide

**Last Updated:** 2025-11-20
**Project:** MyRecoveryPal - Addiction Recovery Support Platform
**Tech Stack:** Django 5.0.10, PostgreSQL, Redis, Celery, Capacitor Mobile

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Codebase Structure](#codebase-structure)
3. [Tech Stack & Dependencies](#tech-stack--dependencies)
4. [Development Setup](#development-setup)
5. [Django Apps & Responsibilities](#django-apps--responsibilities)
6. [Database Models](#database-models)
7. [URL Structure & Routes](#url-structure--routes)
8. [Frontend Architecture](#frontend-architecture)
9. [Configuration & Settings](#configuration--settings)
10. [Development Workflows](#development-workflows)
11. [Key Conventions & Patterns](#key-conventions--patterns)
12. [Testing Strategy](#testing-strategy)
13. [Deployment](#deployment)
14. [Common Tasks](#common-tasks)
15. [Security Considerations](#security-considerations)
16. [Troubleshooting](#troubleshooting)

---

## Project Overview

MyRecoveryPal is a comprehensive Django-based social platform designed to support individuals in addiction recovery. It combines social networking, journaling, resource management, and community support features with mobile app capabilities.

### Core Features
- **Social Networking**: Follow system, activity feeds, posts, comments, likes
- **Recovery Groups**: Create/join groups with challenges and daily check-ins
- **Journaling**: Private recovery journaling with stage-specific prompts
- **Milestone Tracking**: Sobriety date tracking with milestone celebrations
- **Blog Platform**: Community story sharing with trigger warnings
- **Resource Library**: Curated recovery resources (PDFs, articles, interactive tools)
- **Meeting Finder**: AA/NA meeting directory (Meeting Guide API compatible)
- **Support Services**: Directory of treatment centers, helplines, facilities
- **Sponsorship System**: Connect sponsors with sponsees
- **Recovery Pals**: Accountability partner matching
- **Subscriptions**: Stripe-powered premium features
- **Mobile Apps**: iOS & Android via Capacitor
- **Push Notifications**: Firebase Cloud Messaging

### Target Users
- Individuals in recovery from addiction
- Sponsors and mentors
- Support group facilitators
- Recovery service providers

---

## Codebase Structure

```
myrecoverypal/
├── apps/                           # Django applications
│   ├── accounts/                   # User management, social features
│   │   ├── models.py              # User, Milestone, SocialPost, Groups, etc.
│   │   ├── views.py               # Dashboard, profiles, social feed
│   │   ├── urls.py                # /accounts/* routes
│   │   ├── forms.py               # Registration, profile forms
│   │   ├── decorators.py          # Custom auth decorators
│   │   ├── middleware.py          # Rate limiting
│   │   ├── invite_models.py       # Waitlist, invite codes
│   │   ├── payment_models.py      # Stripe subscriptions
│   │   ├── templatetags/          # Custom template tags
│   │   └── management/commands/   # CLI commands
│   │
│   ├── blog/                       # Community blog
│   │   ├── models.py              # Post, Category, Tag, Comment
│   │   ├── views.py               # List, detail, create views
│   │   └── urls.py                # /blog/* routes
│   │
│   ├── journal/                    # Personal journaling
│   │   ├── models.py              # JournalEntry, Prompt, Streak, Reminder
│   │   ├── views.py               # Entry CRUD, prompts
│   │   └── urls.py                # /journal/* routes
│   │
│   ├── core/                       # Core site pages
│   │   ├── views.py               # Homepage, about, contact, error pages
│   │   ├── urls.py                # Root routes
│   │   └── context_processors.py # Global template context
│   │
│   ├── newsletter/                 # Email newsletters
│   │   ├── models.py              # Newsletter, Subscriber, EmailLog
│   │   ├── views.py               # Subscribe/unsubscribe
│   │   └── tasks.py               # Celery newsletter tasks
│   │
│   ├── store/                      # E-commerce (minimal)
│   │   ├── models.py              # Product, Category
│   │   └── views.py               # Product catalog
│   │
│   └── support_services/           # Meeting & service finder
│       ├── models.py              # Meeting, SupportService, Bookmark
│       ├── views.py               # Search, filter, detail
│       └── urls.py                # /support/* routes
│
├── resources/                      # Resource library (separate app)
│   ├── models.py                  # Resource, Category, Type, Rating
│   ├── views.py                   # Browse, detail, download
│   └── management/commands/       # Resource population scripts
│
├── recovery_hub/                   # Django project root
│   ├── settings.py                # Main settings (monolithic)
│   ├── urls.py                    # Root URL configuration
│   ├── wsgi.py                    # WSGI entry point
│   ├── asgi.py                    # ASGI entry point (future WebSocket)
│   ├── celery.py                  # Celery configuration
│   └── sitemaps.py                # SEO sitemap definitions
│
├── templates/                      # Global templates
│   ├── base.html                  # Base template with navbar/footer
│   ├── 404.html, 500.html         # Error pages
│   └── (app templates in apps/*/templates/)
│
├── static/                         # Static assets
│   ├── css/                       # Custom stylesheets
│   ├── js/                        # JavaScript files
│   │   └── main.js                # Core JS functionality
│   ├── images/                    # Icons, screenshots
│   ├── manifest.json              # PWA manifest
│   └── service-worker.js          # PWA offline support
│
├── staticfiles/                    # Collected static files (production)
├── media/                          # User uploads (local dev only)
├── logs/                           # Application logs
│
├── apps/                           # Mobile app configs
│   ├── android/                   # Android Capacitor project
│   └── ios/                       # iOS Capacitor project
│
├── AppIcons/                       # Mobile app icon assets
├── root_files/                     # Files served at root (WhiteNoise)
│
├── build.sh                        # Production build script
├── manage.py                       # Django management script
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies (Capacitor)
├── capacitor.config.json           # Capacitor configuration
├── Procfile                        # Railway deployment config
├── railway.json                    # Railway service config
├── Dockerfile.railway              # Railway Docker config
└── runtime.txt                     # Python version
```

---

## Tech Stack & Dependencies

### Backend Framework
- **Django 5.0.10** - Web framework
- **Python 3.11+** - Language runtime
- **Gunicorn 21.2.0** - WSGI HTTP server

### Database & Caching
- **PostgreSQL** - Primary database (via `DATABASE_URL`)
- **SQLite** - Development fallback
- **Redis 5.0.1** - Caching and message broker
- **django-redis 5.4.0** - Redis cache backend

### Authentication & Authorization
- **django-allauth 0.57.2** - Authentication, registration, social auth
- Custom User model (`apps.accounts.models.User`)

### Background Tasks
- **Celery 5.3.4** - Distributed task queue
- **celery-beat** - Periodic task scheduler
- Newsletter sending, trial expiration checks

### API & REST
- **Django REST Framework 3.14.0** - API framework (minimal usage)
- **django-cors-headers 4.3.1** - CORS handling

### File Storage
- **Cloudinary 1.36.0** - Media CDN (production)
- **django-cloudinary-storage 0.3.0** - Cloudinary backend
- **WhiteNoise 6.6.0** - Static file serving
- **Pillow 10.2.0** - Image processing

### Forms & UI
- **django-crispy-forms 2.1** - Form rendering
- **crispy-bootstrap5 2024.2** - Bootstrap 5 templates
- **django-summernote 0.8.20.0** - WYSIWYG editor

### Payments
- **Stripe 7.11.0** - Payment processing
- Subscription management, invoicing

### Mobile
- **Capacitor 7.4.4** - Web-to-native wrapper
- **@capacitor/android** - Android platform
- **@capacitor/ios** - iOS platform
- **@capacitor/push-notifications 7.0.3** - Push notifications
- **@capacitor/status-bar 7.0.1** - Status bar styling
- **firebase-admin 6.5.0** - Firebase Cloud Messaging

### Monitoring & Logging
- **Sentry 1.40.0** - Error tracking and performance monitoring
- Django logging to `/logs/django.log`

### Development Tools
- **django-extensions** - Optional dev utilities
- **debug-toolbar** - Optional SQL query debugging

---

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 13+ (or use SQLite for local dev)
- Redis 6+ (optional for caching/Celery)
- Node.js 18+ (for mobile app development)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd myrecoverypal
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node dependencies** (for mobile)
   ```bash
   npm install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

6. **Set up database**
   ```bash
   # For SQLite (development)
   python manage.py migrate

   # For PostgreSQL
   # 1. Create database: createdb myrecoverypal
   # 2. Set DATABASE_URL in .env
   # 3. Run migrations
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Populate initial data** (optional)
   ```bash
   # Blog categories and tags
   python manage.py populate_blog_categories
   python manage.py populate_blog_tags

   # Journal prompts
   python manage.py create_journal_prompts

   # Resources
   python manage.py populate_resources

   # Sample data
   python manage.py create_sample_users
   python manage.py create_sample_posts
   ```

9. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

10. **Run development server**
    ```bash
    python manage.py runserver
    ```

11. **Access the application**
    - Web: http://localhost:8000
    - Admin: http://localhost:8000/admin

### Optional: Run Celery Worker

```bash
# In a separate terminal
celery -A recovery_hub worker -l info

# Run beat scheduler (for periodic tasks)
celery -A recovery_hub beat -l info
```

### Optional: Mobile App Development

```bash
# Sync web assets to mobile platforms
npm run cap:sync

# Open in Android Studio
npm run cap:open:android

# Open in Xcode
npm run cap:open:ios
```

---

## Django Apps & Responsibilities

### apps.accounts - User Management & Social Features

**Primary Purpose:** Central hub for authentication, user profiles, social networking, and community features.

**Key Models:**
- `User` - Custom user with recovery-specific fields (sobriety_date, bio, privacy)
- `Milestone` - Track recovery milestones with celebrations
- `DailyCheckIn` - Mood and craving tracking
- `SocialPost` - User posts with comments and likes
- `UserConnection` - Follow/follower relationships
- `SponsorRelationship` - Sponsor/sponsee matching
- `RecoveryPal` - Mutual accountability partnerships
- `RecoveryGroup` - Support groups with memberships
- `GroupChallenge` - Group challenges with daily participation
- `ChallengeParticipant` - Challenge progress and badges
- `ActivityFeed` - Generic activity stream
- `Notification` - Universal notification system
- `Subscription` - Stripe subscription management
- `WaitlistRequest` - Pre-launch waitlist
- `InviteCode` - Invite-only access control

**Key Views:**
- Dashboard, profile management, social feed
- Group management, challenge tracking
- Sponsor/pal matching
- Notification center, messaging
- Subscription/billing management

**Special Features:**
- Custom authentication decorators
- Rate limiting middleware
- Stripe webhook handling
- Activity feed aggregation
- Badge/achievement system

### apps.blog - Community Blog

**Primary Purpose:** Story sharing and community engagement through blog posts.

**Key Models:**
- `Post` - Blog posts with categories, tags, featured images
- `Category` - Post organization
- `Tag` - Post tagging
- `Comment` - Threaded comments

**Features:**
- Trigger warning system
- SEO optimization (meta descriptions, social tags)
- Reading time calculation
- Anonymous posting option
- Moderation workflow

### apps.journal - Private Journaling

**Primary Purpose:** Personal recovery journaling with prompts and tracking.

**Key Models:**
- `JournalEntry` - Private entries with mood/craving tracking
- `JournalPrompt` - Stage-specific recovery prompts
- `JournalStreak` - Consistency tracking
- `JournalReminder` - Email/notification reminders

**Features:**
- Recovery stage filtering (early/middle/ongoing)
- Gratitude logging
- Mood visualization
- Streak gamification
- Privacy controls (entries never shared)

### apps.core - Core Pages

**Primary Purpose:** Static informational pages and site-wide functionality.

**Views:**
- Homepage, About, Contact
- Privacy Policy, Terms of Service, Community Guidelines
- Demo page (feature showcase)
- Crisis resources (immediate help)
- Custom error handlers (404, 500, 403, 400)

**Context Processors:**
- SEO defaults (meta tags, social cards)
- Subscription status (global access)

### apps.newsletter - Email Marketing

**Primary Purpose:** Newsletter management and email campaigns.

**Key Models:**
- `Newsletter` - Email campaigns with HTML content
- `Subscriber` - Email list management
- `EmailLog` - Individual send tracking
- `NewsletterTemplate` - Reusable templates

**Features:**
- Scheduled sending via Celery
- Open/click tracking
- Unsubscribe management
- Template system

### apps.store - E-commerce

**Primary Purpose:** Recovery merchandise and materials (minimal implementation).

**Key Models:**
- `Product` - Products for sale
- `Category` - Product categories

**Note:** Limited functionality - consider expanding or removing.

### apps.support_services - Meeting & Service Finder

**Primary Purpose:** Directory of recovery meetings and support services.

**Key Models:**
- `Meeting` - AA/NA/etc. meetings (Meeting Guide API compliant)
- `SupportService` - Treatment centers, helplines, facilities
- `ServiceSubmission` - Community submissions with moderation
- `UserBookmark` - Saved meetings/services

**Features:**
- Geolocation-based search
- Filter by type, day, time, format (online/hybrid/in-person)
- Meeting Guide API compatibility
- Community submission workflow

### resources - Resource Library

**Primary Purpose:** Educational resources and interactive tools.

**Key Models:**
- `Resource` - PDFs, articles, videos, interactive tools
- `ResourceCategory` - Organization taxonomy
- `ResourceType` - Format types (PDF, video, interactive)
- `ResourceBookmark` - User bookmarks
- `ResourceRating` - Reviews and ratings
- `InteractiveResourceProgress` - Track tool usage
- `CrisisResource` - Emergency helplines

**Features:**
- Access control (free/registered/premium)
- Download tracking
- Interactive component support
- Search and filtering

---

## Database Models

### User Model (`apps.accounts.models.User`)

Extends `AbstractUser` with recovery-specific fields:

```python
User:
  - username (unique)
  - email (unique, required)
  - sobriety_date (DateField, optional)
  - recovery_goals (TextField)
  - is_sponsor (Boolean)
  - bio (TextField)
  - location (CharField)
  - avatar (ImageField)
  - is_profile_public (Boolean)
  - show_sobriety_date (Boolean)
  - allow_messages (Boolean)
  - email_notifications (Boolean)
  - newsletter_subscriber (Boolean)
  - last_seen (DateTimeField)

Methods:
  - get_days_sober()
  - get_sobriety_milestone()
  - get_following(), get_followers()
  - is_following(user)
  - follow_user(user), unfollow_user(user)
  - get_active_sponsor(), get_recovery_pal()
  - get_joined_groups()
```

### Common Model Patterns

**Timestamps:**
```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

**Soft Deletes:**
```python
is_active = models.BooleanField(default=True)
```

**Slugs:**
```python
slug = models.SlugField(unique=True, blank=True)
# Auto-generated in save() method
```

**Choices:**
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('published', 'Published'),
    ('archived', 'Archived'),
]
status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
```

**Generic Foreign Keys (Activity Feed):**
```python
content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
object_id = models.PositiveIntegerField()
content_object = GenericForeignKey('content_type', 'object_id')
```

### Key Relationships

```
User (1) → Many (Milestones, JournalEntries, BlogPosts, Subscriptions)
User (M) ↔ Many (User) via UserConnection (follows)
User (M) ↔ Many (User) via SponsorRelationship (sponsors)
User (M) ↔ Many (RecoveryGroup) via GroupMembership
RecoveryGroup (1) → Many (GroupChallenges)
GroupChallenge (1) → Many (ChallengeParticipants)
Resource (1) → Many (ResourceBookmarks, ResourceRatings)
Newsletter (1) → Many (Subscribers, EmailLogs)
```

---

## URL Structure & Routes

### URL Namespacing

All apps use namespaced URLs for reverse lookups:

```python
# In templates
{% url 'accounts:dashboard' %}
{% url 'blog:post_detail' slug=post.slug %}

# In views
from django.urls import reverse
redirect_url = reverse('accounts:profile', kwargs={'username': username})
```

### Main Routes

```
/                           → core:index (landing page)
/demo/                      → core:demo (feature demo)
/about/                     → core:about
/contact/                   → core:contact

/accounts/
  ├── register/             → accounts:register
  ├── login/                → accounts:login
  ├── logout/               → accounts:logout
  ├── dashboard/            → accounts:dashboard
  ├── profile/<username>/   → accounts:profile
  ├── settings/             → accounts:settings
  ├── social-feed/          → accounts:social_feed
  ├── community/            → accounts:community
  ├── groups/               → accounts:groups
  ├── groups/<id>/          → accounts:group_detail
  ├── challenges/           → accounts:challenges
  ├── sponsors/             → accounts:sponsors
  ├── pals/                 → accounts:pals
  ├── milestones/           → accounts:milestones
  ├── notifications/        → accounts:notifications
  ├── messages/             → accounts:messages
  └── pricing/              → accounts:pricing

/blog/
  ├── /                     → blog:post_list
  ├── write/                → blog:post_create
  ├── post/<slug>/          → blog:post_detail
  ├── category/<slug>/      → blog:category_posts
  └── tag/<slug>/           → blog:tag_posts

/journal/
  ├── /                     → journal:entry_list
  ├── write/                → journal:entry_create
  └── entry/<pk>/           → journal:entry_detail

/resources/
  ├── /                     → resources:resource_list
  ├── category/<slug>/      → resources:category
  └── <slug>/               → resources:resource_detail

/support/
  ├── meetings/             → support:meeting_list
  ├── meetings/<id>/        → support:meeting_detail
  ├── services/             → support:service_list
  └── crisis/               → support:crisis_resources

/newsletter/
  ├── subscribe/            → newsletter:subscribe
  └── unsubscribe/<token>/  → newsletter:unsubscribe

/admin/                     → Django admin
/summernote/                → Summernote editor uploads
/sitemap.xml                → SEO sitemap
/robots.txt                 → Search engine directives
```

---

## Frontend Architecture

### Template Structure

**Base Template (`templates/base.html`):**
- Site-wide navbar with authentication state
- Flash messages (Django messages framework)
- Footer with links
- Common CSS/JS includes
- Block structure for inheritance

**Block Structure:**
```django
{% block title %}{% endblock %}
{% block extra_css %}{% endblock %}
{% block content %}{% endblock %}
{% block extra_js %}{% endblock %}
```

**App Templates:**
Located in `apps/*/templates/` directories, namespaced by app:
```
apps/accounts/templates/accounts/
  ├── dashboard.html
  ├── profile.html
  ├── social_feed.html
  └── ...
```

### Static Files

**CSS:**
- Bootstrap 5 (via CDN or crispy-bootstrap5)
- Custom styles in `/static/css/`
- Component-specific styles

**JavaScript:**
- Vanilla JavaScript (no major framework)
- `/static/js/main.js` - Core functionality
- jQuery (minimal usage, consider removing)
- AJAX for real-time updates (likes, notifications)

**Progressive Web App:**
- `/static/manifest.json` - PWA manifest
- `/static/service-worker.js` - Offline support
- Installable on mobile devices

### Forms

**Crispy Forms Pattern:**
```django
{% load crispy_forms_tags %}
<form method="post">
  {% csrf_token %}
  {{ form|crispy }}
  <button type="submit">Submit</button>
</form>
```

**Form Helper (Python):**
```python
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class MyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save'))
```

### Template Tags

**Custom Tags (`apps/accounts/templatetags/`):**
```django
{% load subscription_tags %}
{% if user|has_active_subscription %}
  <!-- Premium content -->
{% endif %}

{% load accounts_tags %}
{% user_following_count user %}
```

### Context Processors

Global variables available in all templates:

```python
# settings.py TEMPLATES['OPTIONS']['context_processors']
- 'apps.core.context_processors.seo_defaults'
- 'apps.accounts.context_processors.subscription_context'

# Available in templates:
{{ SEO_TITLE }}
{{ SEO_DESCRIPTION }}
{{ user.subscription }}  # If authenticated
```

---

## Configuration & Settings

### Environment Variables (`.env`)

**Required:**
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True  # False in production
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
```

**Optional:**
```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Email (SendGrid)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=MyRecoveryPal <noreply@myrecoverypal.com>

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Sentry
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=development

# Site
SITE_URL=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Settings Organization

**Main Settings:** `recovery_hub/settings.py` (monolithic file)

**Key Sections:**
1. Security (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
2. Installed apps
3. Middleware
4. Templates
5. Database (PostgreSQL via dj-database-url)
6. Authentication (allauth configuration)
7. Caching (Redis with local memory fallback)
8. Static files (WhiteNoise)
9. Media files (Cloudinary)
10. Email configuration
11. Celery configuration
12. Third-party integrations (Stripe, Sentry)
13. Logging

### Important Settings

**Custom User Model:**
```python
AUTH_USER_MODEL = 'accounts.User'
```

**Authentication Backend:**
```python
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
```

**Login URLs:**
```python
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/'
```

**Email Verification:**
```python
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # or 'optional' for development
```

**Static/Media Files:**
```python
# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (Cloudinary in production)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

---

## Development Workflows

### Git Workflow

**Branch Strategy:**
- `main` - Production branch (auto-deploys to Railway)
- Feature branches: `feature/description` or `claude/session-id`
- Hotfix branches: `hotfix/description`

**Commit Guidelines:**
- Clear, descriptive commit messages
- Reference issue numbers if applicable
- Atomic commits (one logical change per commit)

### Development Cycle

1. **Pull latest changes**
   ```bash
   git pull origin main
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **Make changes**
   - Edit code
   - Write migrations: `python manage.py makemigrations`
   - Run migrations: `python manage.py migrate`
   - Test manually (no automated tests yet)

4. **Commit changes**
   ```bash
   git add .
   git commit -m "Add new feature: description"
   ```

5. **Push to remote**
   ```bash
   git push -u origin feature/new-feature
   ```

6. **Create Pull Request**
   - Use GitHub PR interface
   - Request review if applicable
   - Merge to main when approved

7. **Auto-deployment**
   - Railway/Render detects main branch changes
   - Runs `build.sh` script
   - Deploys automatically

### Database Migrations

**Creating Migrations:**
```bash
# After model changes
python manage.py makemigrations

# Named migration
python manage.py makemigrations accounts --name add_new_field

# Check migration SQL (without running)
python manage.py sqlmigrate accounts 0001

# Apply migrations
python manage.py migrate

# Rollback to specific migration
python manage.py migrate accounts 0003
```

**Migration Best Practices:**
- Always review generated migrations before committing
- Use `RunPython` for data migrations
- Add indexes for frequently queried fields
- Use `db_index=True` on foreign keys
- Never edit applied migrations (create new ones)

### Static Files Management

**Development:**
```bash
# Static files auto-served from STATICFILES_DIRS
python manage.py runserver
```

**Production:**
```bash
# Collect static files to STATIC_ROOT
python manage.py collectstatic --noinput

# WhiteNoise serves compressed files
```

### Celery Tasks

**Running Workers:**
```bash
# Worker (processes tasks)
celery -A recovery_hub worker -l info

# Beat scheduler (periodic tasks)
celery -A recovery_hub beat -l info

# Combined (development only)
celery -A recovery_hub worker -l info -B
```

**Monitoring:**
```bash
# Flower (web-based monitoring)
pip install flower
celery -A recovery_hub flower
# Visit http://localhost:5555
```

### Mobile App Sync

**Sync web changes to mobile:**
```bash
# Sync all platforms
npm run cap:sync

# Sync specific platform
npm run cap:sync:android
npm run cap:sync:ios

# Open in IDE
npm run cap:open:android  # Android Studio
npm run cap:open:ios      # Xcode
```

**Build mobile apps:**
```bash
# Android debug build
npm run build:android:debug

# Android release build (for Play Store)
npm run build:android:release
```

---

## Key Conventions & Patterns

### Python Code Style

**PEP 8 Compliance:**
- Snake_case for variables, functions, methods
- PascalCase for class names
- CAPS_SNAKE_CASE for constants
- 4 spaces for indentation

**Django Conventions:**
```python
# Model naming (singular)
class User(models.Model):
    pass

# View naming (descriptive)
def user_profile_view(request, username):
    pass

class PostListView(ListView):
    pass

# URL naming (noun or verb_noun)
path('dashboard/', views.dashboard, name='dashboard')
path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail')
```

### Model Patterns

**Always Include Timestamps:**
```python
class MyModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Use Verbose Names:**
```python
class Meta:
    verbose_name = 'Recovery Group'
    verbose_name_plural = 'Recovery Groups'
    ordering = ['-created_at']
```

**Indexes for Performance:**
```python
class Meta:
    indexes = [
        models.Index(fields=['user', '-created_at']),
        models.Index(fields=['status', 'published_at']),
    ]
```

**String Representation:**
```python
def __str__(self):
    return self.title  # or meaningful identifier
```

**Absolute URL:**
```python
def get_absolute_url(self):
    return reverse('app:model_detail', kwargs={'slug': self.slug})
```

### View Patterns

**Class-Based Views (Preferred):**
```python
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 20

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content', 'category']
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
```

**Function-Based Views (Complex Logic):**
```python
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

@login_required
def custom_view(request):
    if request.method == 'POST':
        # Handle form submission
        pass
    return render(request, 'template.html', context)
```

### Template Patterns

**Inheritance:**
```django
{% extends 'base.html' %}

{% block title %}Page Title{% endblock %}

{% block content %}
  <h1>Content Here</h1>
{% endblock %}
```

**Include Partials:**
```django
{% include 'partials/navbar.html' %}
{% include 'partials/post_card.html' with post=post %}
```

**Loops with Empty:**
```django
{% for post in posts %}
  <div>{{ post.title }}</div>
{% empty %}
  <p>No posts found.</p>
{% endfor %}
```

**URL Reverse:**
```django
<a href="{% url 'blog:post_detail' slug=post.slug %}">
  {{ post.title }}
</a>
```

### Form Patterns

**ModelForm:**
```python
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category', 'tags']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        # Custom validation
        return title
```

**Form Validation:**
```python
def clean(self):
    cleaned_data = super().clean()
    # Cross-field validation
    return cleaned_data
```

### URL Patterns

**App-Level URLs:**
```python
# apps/blog/urls.py
from django.urls import path
from . import views

app_name = 'blog'  # Namespace

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
]
```

**Project-Level URLs:**
```python
# recovery_hub/urls.py
from django.urls import path, include

urlpatterns = [
    path('blog/', include('apps.blog.urls', namespace='blog')),
]
```

### Query Optimization

**Use select_related (1-to-1, ForeignKey):**
```python
posts = Post.objects.select_related('author', 'category').all()
```

**Use prefetch_related (Many-to-Many, Reverse FK):**
```python
posts = Post.objects.prefetch_related('tags', 'comments').all()
```

**Avoid N+1 Queries:**
```python
# Bad
for post in posts:
    print(post.author.username)  # Query per post

# Good
posts = Post.objects.select_related('author')
for post in posts:
    print(post.author.username)  # Single query
```

### Recovery-Specific Conventions

**Sobriety Date Handling:**
```python
# Always use timezone-aware dates
from django.utils import timezone

days_sober = (timezone.now().date() - user.sobriety_date).days
```

**Privacy First:**
- Journal entries are ALWAYS private
- Profile visibility controlled by `is_profile_public`
- Anonymous posting options for sensitive content

**Trigger Warnings:**
- Blog posts can be marked with trigger warnings
- Display warnings before content

**Recovery Stages:**
```python
RECOVERY_STAGES = [
    ('early', 'Early Recovery (0-90 days)'),
    ('middle', 'Middle Recovery (90 days - 1 year)'),
    ('ongoing', 'Ongoing Recovery (1+ years)'),
]
```

---

## Testing Strategy

### Current State
**⚠️ NO AUTOMATED TESTING FRAMEWORK CURRENTLY CONFIGURED**

### Testing Tools Available (Not Configured)
- Django's built-in test framework (unittest)
- pytest-django (recommended)
- coverage.py (code coverage)
- factory_boy (test data generation)

### Recommended Testing Setup

**1. Install testing dependencies:**
```bash
pip install pytest pytest-django pytest-cov factory-boy faker
```

**2. Create pytest configuration (`pytest.ini`):**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = recovery_hub.settings
python_files = tests.py test_*.py *_tests.py
addopts = --cov=apps --cov=resources --cov-report=html --cov-report=term
```

**3. Write tests:**
```python
# apps/accounts/tests/test_models.py
import pytest
from apps.accounts.models import User

@pytest.mark.django_db
def test_user_days_sober():
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='password123',
        sobriety_date='2024-01-01'
    )
    assert user.get_days_sober() > 0
```

**4. Run tests:**
```bash
pytest
pytest --cov  # With coverage
pytest apps/accounts/  # Specific app
```

### Manual Testing Checklist

Until automated tests are implemented:

- [ ] Registration flow
- [ ] Login/logout
- [ ] Profile editing
- [ ] Blog post creation/editing
- [ ] Journal entry creation
- [ ] Group creation/joining
- [ ] Challenge participation
- [ ] Follow/unfollow users
- [ ] Subscription purchase (Stripe test mode)
- [ ] Email notifications
- [ ] Mobile app (iOS/Android)

---

## Deployment

### Platforms

**Primary: Railway**
- Automatic deployment from `main` branch
- Configuration: `railway.json`, `Procfile`
- Build command: `./build.sh`
- Start command: `gunicorn recovery_hub.wsgi:application`

**Alternative: Render**
- Configuration: `render.yaml`
- Similar build/start commands

### Build Process (`build.sh`)

```bash
#!/bin/bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p staticfiles logs media

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# Generate sitemap
python manage.py generate_sitemap

# Copy SEO files
cp sitemap.xml staticfiles/
cp root_files/* staticfiles/ 2>/dev/null || true
```

### Environment Variables (Production)

**Required in Railway/Render:**
```
SECRET_KEY=<strong-random-key>
DEBUG=False
DATABASE_URL=<postgresql-url>
REDIS_URL=<redis-url>
ALLOWED_HOSTS=myrecoverypal.com,www.myrecoverypal.com
CLOUDINARY_CLOUD_NAME=<cloudinary-name>
CLOUDINARY_API_KEY=<cloudinary-key>
CLOUDINARY_API_SECRET=<cloudinary-secret>
STRIPE_SECRET_KEY=<live-stripe-key>
STRIPE_PUBLISHABLE_KEY=<live-stripe-key>
SENTRY_DSN=<sentry-dsn>
SENTRY_ENVIRONMENT=production
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
```

### Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for caching
- [ ] Set up Cloudinary for media storage
- [ ] Configure SendGrid for email
- [ ] Set up Stripe live keys
- [ ] Configure Sentry for error monitoring
- [ ] Set up SSL certificate (automatic on Railway/Render)
- [ ] Run migrations
- [ ] Collect static files
- [ ] Test email sending
- [ ] Test Stripe payments
- [ ] Test mobile app connections
- [ ] Set up Celery worker (separate service)
- [ ] Configure backup strategy

### Celery Worker Setup (Railway)

Create separate service in Railway:
- Build command: (none)
- Start command: `celery -A recovery_hub worker -l info`
- Environment variables: Same as web service

### Monitoring

**Sentry:**
- Error tracking: https://sentry.io
- Performance monitoring enabled
- Sample rate: 10% (configurable)

**Railway Logs:**
```bash
# View via Railway dashboard
# Or use Railway CLI
railway logs
```

**Database Backups:**
- Railway automatic backups (paid plan)
- Manual: `pg_dump` via Railway CLI

---

## Common Tasks

### Create a New Django App

```bash
# Create app in apps/ directory
cd apps
django-admin startapp newapp

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS = [
    # ...
    'apps.newapp',
]

# Create urls.py in app
# apps/newapp/urls.py
from django.urls import path
from . import views

app_name = 'newapp'
urlpatterns = [
    path('', views.index, name='index'),
]

# Include in project urls.py
# recovery_hub/urls.py
urlpatterns = [
    path('newapp/', include('apps.newapp.urls', namespace='newapp')),
]
```

### Add a New Model

```python
# apps/myapp/models.py
from django.db import models
from apps.accounts.models import User

class MyModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mymodels')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```

```bash
# Create and run migrations
python manage.py makemigrations
python manage.py migrate

# Register in admin
# apps/myapp/admin.py
from django.contrib import admin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
```

### Add a Management Command

```python
# apps/myapp/management/commands/my_command.py
from django.core.management.base import BaseCommand
from apps.myapp.models import MyModel

class Command(BaseCommand):
    help = 'Description of what this command does'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10)

    def handle(self, *args, **options):
        limit = options['limit']
        # Command logic here
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {limit} items'))
```

```bash
# Run command
python manage.py my_command --limit=20
```

### Add a Celery Task

```python
# apps/myapp/tasks.py
from celery import shared_task
from .models import MyModel

@shared_task
def process_my_model(model_id):
    """Process a MyModel instance"""
    try:
        obj = MyModel.objects.get(id=model_id)
        # Task logic here
        return f'Processed {obj.title}'
    except MyModel.DoesNotExist:
        return f'MyModel {model_id} not found'

# Schedule periodic task in settings.py
CELERY_BEAT_SCHEDULE = {
    'process-daily': {
        'task': 'apps.myapp.tasks.process_my_model',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

```python
# Call task from views
from .tasks import process_my_model

# Synchronous (blocking)
result = process_my_model(obj.id)

# Asynchronous (recommended)
process_my_model.delay(obj.id)
```

### Add a Custom Template Tag

```python
# apps/myapp/templatetags/myapp_tags.py
from django import template

register = template.Library()

@register.simple_tag
def my_tag(value):
    """Custom template tag"""
    return value.upper()

@register.filter
def my_filter(value, arg):
    """Custom template filter"""
    return f"{value} - {arg}"
```

```django
{% load myapp_tags %}

{{ "hello"|my_filter:"world" }}
{% my_tag "greeting" %}
```

### Add API Endpoint (DRF)

```python
# apps/myapp/serializers.py
from rest_framework import serializers
from .models import MyModel

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ['id', 'title', 'content', 'created_at']

# apps/myapp/api_views.py
from rest_framework import generics
from .models import MyModel
from .serializers import MyModelSerializer

class MyModelListAPI(generics.ListAPIView):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer

# apps/myapp/urls.py
from django.urls import path
from .api_views import MyModelListAPI

urlpatterns = [
    path('api/mymodels/', MyModelListAPI.as_view(), name='mymodel_api_list'),
]
```

### Update User Model (Add Fields)

```python
# apps/accounts/models.py
class User(AbstractUser):
    # Add new field
    new_field = models.CharField(max_length=100, blank=True)
```

```bash
# Create migration
python manage.py makemigrations accounts

# Review migration
cat apps/accounts/migrations/000X_auto_*.py

# Apply migration
python manage.py migrate accounts
```

---

## Security Considerations

### Authentication & Authorization

**Always use `@login_required` or `LoginRequiredMixin`:**
```python
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def my_view(request):
    pass

class MyView(LoginRequiredMixin, View):
    pass
```

**Permission checks:**
```python
from django.contrib.auth.decorators import permission_required

@permission_required('app.add_model')
def my_view(request):
    pass

# Or in views
if not request.user.has_perm('app.change_model'):
    return HttpResponseForbidden()
```

### CSRF Protection

**Always use `{% csrf_token %}` in forms:**
```django
<form method="post">
  {% csrf_token %}
  <!-- form fields -->
</form>
```

**AJAX requests:**
```javascript
// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Include in AJAX requests
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
});
```

### SQL Injection Prevention

**Always use parameterized queries:**
```python
# Good (parameterized)
User.objects.filter(username=username)

# Good (raw SQL with params)
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM users WHERE username = %s", [username])

# Bad (vulnerable to SQL injection)
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

### XSS Prevention

**Django auto-escapes template variables:**
```django
{{ user_input }}  <!-- Automatically escaped -->

{% autoescape off %}
  {{ trusted_html|safe }}  <!-- Only for trusted content -->
{% endautoescape %}
```

**Sanitize user input:**
```python
from django.utils.html import escape

safe_text = escape(user_input)
```

### Sensitive Data

**Never commit secrets to Git:**
- Use `.env` files (in `.gitignore`)
- Environment variables in production
- Django's `SECRET_KEY` should be random and secret

**Environment variables:**
```python
# settings.py
import os
SECRET_KEY = os.environ.get('SECRET_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
```

### Rate Limiting

**Custom middleware in place:**
```python
# apps/accounts/middleware.py
class RateLimitMiddleware
```

**Applied to API endpoints to prevent abuse**

### HTTPS Enforcement

**Production settings:**
```python
# Redirect HTTP to HTTPS
SECURE_SSL_REDIRECT = not DEBUG

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
```

### Privacy Considerations

**Recovery-specific privacy:**
- Journal entries are NEVER shared
- Profile visibility controlled by user
- Sobriety date visibility optional
- Anonymous posting available for sensitive content
- Message privacy enforced

**Data minimization:**
- Only collect necessary data
- Allow users to delete their data
- Respect privacy settings in all queries

---

## Troubleshooting

### Common Issues

**Issue: Migrations conflict**
```bash
# Solution: Merge migrations
python manage.py makemigrations --merge

# Or use management command
python manage.py fix_migration_conflict
```

**Issue: Static files not loading in production**
```bash
# Solution: Collect static files
python manage.py collectstatic --noinput

# Check STATIC_ROOT and STATICFILES_STORAGE settings
# Verify WhiteNoise in MIDDLEWARE
```

**Issue: Database connection errors**
```bash
# Check DATABASE_URL format
# PostgreSQL: postgres://user:password@host:port/dbname
# Verify PostgreSQL is running
# Check credentials and network access
```

**Issue: Redis connection errors**
```bash
# Check REDIS_URL format
# redis://localhost:6379/0
# Verify Redis is running: redis-cli ping
# Fallback to local memory cache if Redis unavailable
```

**Issue: Celery tasks not running**
```bash
# Verify worker is running
celery -A recovery_hub worker -l info

# Check broker connection (Redis)
# Verify task is registered: celery -A recovery_hub inspect registered

# Check beat scheduler for periodic tasks
celery -A recovery_hub beat -l info
```

**Issue: Email not sending**
```bash
# Test SMTP connection
python manage.py test_smtp

# Test email sending
python manage.py test_email recipient@example.com

# Check EMAIL_BACKEND setting
# Verify SendGrid API key
# Check Sentry for errors
```

**Issue: Stripe webhooks failing**
```bash
# Use Stripe CLI for local testing
stripe listen --forward-to localhost:8000/accounts/stripe/webhook/

# Verify webhook signature
# Check STRIPE_SECRET_KEY
# Review webhook logs in Stripe dashboard
```

**Issue: Mobile app not connecting**
```bash
# Check server URL in capacitor.config.json
# Verify CORS settings
# Check ALLOWED_HOSTS
# Test API endpoints directly
# Review mobile app logs
```

**Issue: Cloudinary uploads failing**
```bash
# Verify Cloudinary credentials in .env
# Check CLOUDINARY_CLOUD_NAME, API_KEY, API_SECRET
# Test with Cloudinary dashboard
# Check file size limits
```

**Issue: Permission denied errors**
```bash
# Check file/directory permissions
chmod 755 staticfiles/ media/ logs/

# Verify user running process has write access
# Check SELinux/AppArmor if applicable
```

### Debugging Tools

**Django Debug Toolbar (Development):**
```bash
pip install django-debug-toolbar

# Add to INSTALLED_APPS and MIDDLEWARE
# Access at /__debug__/
```

**Django Shell:**
```bash
python manage.py shell

# Test queries, models, functions
>>> from apps.accounts.models import User
>>> User.objects.count()
```

**Database Shell:**
```bash
python manage.py dbshell

# Direct SQL access
```

**Logs:**
```bash
# Application logs
tail -f logs/django.log

# Railway logs
railway logs

# Sentry dashboard for production errors
```

### Performance Optimization

**Database Query Optimization:**
```python
# Use Django Debug Toolbar to identify N+1 queries
# Add select_related() and prefetch_related()
# Create database indexes
# Use .only() and .defer() to limit fields
```

**Caching:**
```python
from django.core.cache import cache

# Cache expensive queries
result = cache.get('my_key')
if result is None:
    result = expensive_operation()
    cache.set('my_key', result, 3600)  # 1 hour
```

**Static File Optimization:**
```bash
# WhiteNoise compression enabled
# Use CDN for media (Cloudinary)
# Minimize CSS/JS
# Enable browser caching
```

---

## Additional Resources

### Documentation
- **Django Docs:** https://docs.djangoproject.com/
- **Django REST Framework:** https://www.django-rest-framework.org/
- **Celery:** https://docs.celeryproject.org/
- **Capacitor:** https://capacitorjs.com/docs
- **Stripe:** https://stripe.com/docs
- **Cloudinary:** https://cloudinary.com/documentation

### Project-Specific Guides
- `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions
- `MOBILE_APP_GUIDE.md` - Mobile app development
- `PUSH_NOTIFICATIONS_SETUP.md` - Firebase push notifications
- `STRIPE_SETUP_GUIDE.md` - Payment integration
- `SENTRY_SETUP.md` - Error monitoring
- `SECURITY_AUDIT.md` - Security best practices
- `MARKETING_STRATEGY.md` - Marketing and growth
- `MONETIZATION_STRATEGY.md` - Revenue models

### Support
- **GitHub Issues:** Report bugs and request features
- **Sentry:** Production error tracking
- **Railway Support:** Deployment issues

---

## Recovery-Specific Guidelines

### Content Moderation

**Trigger Warnings:**
- Always provide trigger warnings for sensitive content
- Categories: substance use details, relapse, trauma
- Implemented in blog posts, support resources

**Community Guidelines:**
- No promotion of substance use
- Respect anonymity and privacy
- No medical advice (not a replacement for professional help)
- Crisis resources prominently displayed

### Crisis Resources

**Always available:**
- National helplines (SAMHSA, Crisis Text Line)
- Local resources based on location
- Displayed on: `/support/crisis/`, footer, error pages
- Never hide crisis resources behind login

### Privacy First

**Journaling:**
- Private by default
- Never share journal entries
- No social features for journals

**Anonymity Options:**
- Allow anonymous posting in forums
- Optional username display
- Control profile visibility

### Sobriety Date Handling

**Best Practices:**
- Never assume sobriety date exists
- Allow users to hide sobriety date
- Respect different recovery paths (harm reduction, abstinence)
- Celebrate milestones sensitively

**Calculations:**
```python
# Always check for None
if user.sobriety_date:
    days_sober = user.get_days_sober()
else:
    days_sober = None
```

### Inclusive Language

**Recovery Paths:**
- Support all recovery paths (12-step, SMART Recovery, harm reduction)
- Avoid prescriptive language ("must", "should")
- Person-first language ("person in recovery" not "addict")

**Diversity:**
- Inclusive of all substances (alcohol, drugs, behavioral addictions)
- Respect different cultural approaches
- Accessible design (WCAG compliance goal)

---

## Changelog

**2025-11-20:** Initial CLAUDE.md creation
- Comprehensive codebase documentation
- Development workflows and conventions
- Deployment and troubleshooting guides
- Recovery-specific guidelines

---

## Notes for AI Assistants

When working on this codebase:

1. **Always check for existing patterns** before implementing new features
2. **Follow Django best practices** and existing conventions
3. **Prioritize user privacy** especially for recovery-related data
4. **Test manually** (no automated tests yet - consider adding them!)
5. **Use migrations** for all model changes
6. **Update this document** when making significant architectural changes
7. **Consider mobile app impact** when changing APIs or URLs
8. **Respect the recovery community** with inclusive, sensitive language
9. **Security first** - never expose sensitive data
10. **Document as you go** - future you will thank present you

**Common AI Assistant Tasks:**
- Adding new models/views/templates
- Debugging deployment issues
- Writing migrations
- Optimizing queries
- Implementing new features
- Security reviews
- Code refactoring

**Questions to Ask User:**
- "Does this feature need mobile app support?"
- "Should this be available to free or premium users?"
- "Is this sensitive content requiring trigger warnings?"
- "Does this need to be private/anonymous?"
- "Should we send notifications for this?"

---

**End of CLAUDE.md**
