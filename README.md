# Recovery Journey Website

A Django-based web application designed to support individuals in addiction recovery through blogging, journaling, resources, and community features.

## Features

- **User Authentication**: Custom user model with recovery-specific fields
- **Blog System**: Share stories and experiences with the community
- **Personal Journal**: Private journaling with recovery-focused prompts
- **Resource Library**: Curated recovery resources and tools
- **E-commerce Store**: Recovery-themed merchandise and materials
- **Newsletter**: Stay connected with weekly updates
- **Milestone Tracking**: Celebrate recovery milestones

## Tech Stack

- Django 5.0
- PostgreSQL
- Redis (caching & Celery)
- Celery (background tasks)
- Stripe (payments)
- AWS S3 (media storage in production)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd recovery_website# myrecoverypal
