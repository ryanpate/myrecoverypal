import { defineRailway, github, preserve, project, service } from "railway/iac";

// Replaces railway.json (Config as Code, no longer read after 2026-12-01).
//
// This file manages ONLY the two services built from this repository. The
// Postgres and Redis databases and their volumes are deliberately not declared
// here: a full-project import proposed changing the Postgres image, which must
// never be applied to the production database. See
// https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "myrecoverypal";

// Both services build the same image from Dockerfile.railway.
const build = {
  builder: "DOCKERFILE" as const,
  dockerfilePath: "Dockerfile.railway",
  // Skip deploys for changes confined to docs, the mobile projects and root *.md
  watchPatterns: ["**", "!/docs/**", "!/ios/**", "!/android/**", "!/AppIcons/**", "!/*.md"],
};

// railway.json also set restartPolicyType ON_FAILURE / 10 retries. That is
// Railway's default, so it is not declared here (declaring it shows up as
// permanent drift in `railway config plan`).

export default defineRailway(() => {
  const myrecoverypal = github("ryanpate/myrecoverypal", { checkSuites: false });

  // Django app. The container's CMD is start.sh (migrations, then gunicorn).
  const web = service("web", {
    source: myrecoverypal,
    build,
    // Answered by HealthCheckMiddleware; start.sh runs migrations first, hence the long timeout.
    healthcheck: "/healthz/",
    healthcheckTimeout: 300,
    replicas: { "us-east4-eqdc4a": 1 },
    domains: ["myrecoverypal.com", "www.myrecoverypal.com"],
    // Values live in Railway; preserve() keeps whatever is set there.
    env: {
      ADMIN_SECRET_KEY: preserve(),
      ALLOWED_HOSTS: preserve(),
      ANTHROPIC_API_KEY: preserve(),
      APNS_KEY_CONTENT: preserve(),
      APNS_KEY_ID: preserve(),
      APNS_TEAM_ID: preserve(),
      CLOUDINARY_API_KEY: preserve(),
      CLOUDINARY_API_SECRET: preserve(),
      CLOUDINARY_CLOUD_NAME: preserve(),
      CLOUDINARY_URL: preserve(),
      DATABASE_URL: preserve(),
      DEBUG: preserve(),
      DEFAULT_FROM_EMAIL: preserve(),
      DISABLE_COLLECTSTATIC: preserve(),
      DJANGO_SETTINGS_MODULE: preserve(),
      DJANGO_SUPERUSER_EMAIL: preserve(),
      DJANGO_SUPERUSER_PASSWORD: preserve(),
      EMAIL_BACKEND: preserve(),
      EMAIL_HOST: preserve(),
      EMAIL_HOST_PASSWORD: preserve(),
      EMAIL_HOST_USER: preserve(),
      EMAIL_PORT: preserve(),
      EMAIL_TIMEOUT: preserve(),
      EMAIL_USE_SSL: preserve(),
      EMAIL_USE_TLS: preserve(),
      PRINTIFY_API_KEY: preserve(),
      PRINTIFY_WEBHOOK_SECRET: preserve(),
      REDIS_URL: preserve(),
      RESEND_API_KEY: preserve(),
      REVENUECAT_IOS_API_KEY: preserve(),
      SECRET_KEY: preserve(),
      SENTRY_DSN: preserve(),
      SENTRY_ENVIRONMENT: preserve(),
      SERVER_EMAIL: preserve(),
      SITE_URL: preserve(),
      STRIPE_PUBLISHABLE_KEY: preserve(),
      STRIPE_SECRET_KEY: preserve(),
      STRIPE_WEBHOOK_SECRET: preserve(),
    },
  });

  // Celery worker + beat, same image with a different start command. No HTTP
  // server, so no health check.
  const celeryWorker = service("celery-worker", {
    source: myrecoverypal,
    build,
    start: "celery -A recovery_hub worker -l info -B --pool=solo",
    replicas: { "us-east4-eqdc4a": 1 },
    env: {
      ANTHROPIC_API_KEY: preserve(),
      APNS_KEY_CONTENT: preserve(),
      APNS_KEY_ID: preserve(),
      APNS_TEAM_ID: preserve(),
      CLOUDINARY_API_KEY: preserve(),
      CLOUDINARY_API_SECRET: preserve(),
      CLOUDINARY_CLOUD_NAME: preserve(),
      DATABASE_URL: preserve(),
      DEBUG: preserve(),
      DEFAULT_FROM_EMAIL: preserve(),
      DJANGO_SETTINGS_MODULE: preserve(),
      EMAIL_BACKEND: preserve(),
      EMAIL_HOST: preserve(),
      EMAIL_HOST_PASSWORD: preserve(),
      EMAIL_HOST_USER: preserve(),
      EMAIL_PORT: preserve(),
      EMAIL_USE_SSL: preserve(),
      EMAIL_USE_TLS: preserve(),
      PRINTIFY_API_KEY: preserve(),
      REDIS_URL: preserve(),
      RESEND_API_KEY: preserve(),
      REVENUECAT_IOS_API_KEY: preserve(),
      SECRET_KEY: preserve(),
      SENTRY_DSN: preserve(),
      SENTRY_ENVIRONMENT: preserve(),
      SITE_URL: preserve(),
    },
  });

  return project("responsible-education", {
    resources: [web, celeryWorker],
  });
});
