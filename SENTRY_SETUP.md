# Sentry Error Monitoring Setup Guide

**Date:** 2025-11-14
**For:** MyRecoveryPal Production Deployment

---

## What is Sentry?

Sentry is an error tracking and performance monitoring platform that helps you:
- **Catch errors in real-time** before users report them
- **Get detailed stack traces** to debug issues quickly
- **Monitor performance** and identify slow endpoints
- **Track releases** to see which version introduced a bug
- **Set up alerts** for critical errors

**Cost:** Free tier includes 5,000 errors/month (sufficient for early stage)

---

## Setup Instructions

### Step 1: Create a Sentry Account

1. Go to https://sentry.io/signup/
2. Sign up with your email or GitHub account
3. Create a new organization (e.g., "MyRecoveryPal")

### Step 2: Create a New Project

1. Click "Create Project"
2. Select **Django** as the platform
3. Set alert frequency: **Alert me on every new issue**
4. Name your project: `myrecoverypal-production`
5. Click "Create Project"

### Step 3: Get Your DSN

After creating the project, Sentry will show you a DSN (Data Source Name). It looks like:

```
https://examplePublicKey@o0.ingest.sentry.io/0
```

**Copy this DSN** - you'll need it for the next step.

### Step 4: Add Sentry DSN to Railway

1. Go to your Railway dashboard
2. Select your MyRecoveryPal project
3. Click on the "Variables" tab
4. Add a new variable:
   - **Name:** `SENTRY_DSN`
   - **Value:** (paste the DSN you copied)

5. Add another variable for environment:
   - **Name:** `SENTRY_ENVIRONMENT`
   - **Value:** `production`

6. Click "Deploy" to restart with new environment variables

### Step 5: Verify Installation

1. After deployment, trigger a test error:
   - Visit: `https://your-site.com/sentry-debug/` (if you create this endpoint)
   - Or wait for a real error to occur

2. Check your Sentry dashboard at https://sentry.io
3. You should see the error appear within seconds

---

## Optional: Create a Test Error Endpoint

Add this to your `apps/core/views.py` for testing (REMOVE after testing):

```python
def trigger_error(request):
    """Test view to trigger a Sentry error"""
    division_by_zero = 1 / 0
    return HttpResponse("This won't be reached")
```

Add to `apps/core/urls.py`:

```python
urlpatterns = [
    # ... existing patterns ...
    path('sentry-debug/', views.trigger_error, name='sentry_debug'),  # REMOVE after testing
]
```

Visit `https://your-site.com/sentry-debug/` to trigger an error and verify Sentry is working.

**IMPORTANT:** Remove this endpoint after testing!

---

## Understanding Sentry Configuration

The following settings have been configured in `settings.py`:

### 1. Integrations

```python
integrations=[
    DjangoIntegration(),      # Django-specific error tracking
    RedisIntegration(),       # Redis performance monitoring
    CeleryIntegration(),      # Celery task monitoring
]
```

### 2. Performance Monitoring

```python
traces_sample_rate=0.1  # Capture 10% of transactions
```

**What this means:**
- Sentry will monitor 10% of your web requests for performance
- This helps identify slow endpoints
- Set to `1.0` to monitor 100% (may increase costs on free tier)
- Set to `0` to disable performance monitoring entirely

### 3. Error Sampling

```python
sample_rate=1.0  # Capture 100% of errors
```

**What this means:**
- All errors will be sent to Sentry
- You can reduce this to `0.5` (50%) if you hit free tier limits
- Never set below `0.1` (10%) or you might miss critical errors

### 4. PII (Personal Information)

```python
send_default_pii=False
```

**What this means:**
- User emails, IPs, and other personal data will NOT be sent to Sentry
- This protects user privacy
- Set to `True` only if you need to track specific users (not recommended for recovery app)

### 5. Environment & Release Tracking

```python
environment='production'  # or 'staging', 'development'
release=os.environ.get('RAILWAY_GIT_COMMIT_SHA', 'unknown')
```

**What this means:**
- Errors are tagged with environment (helps separate production vs staging issues)
- Release tracking shows which git commit introduced a bug
- Railway automatically provides the commit SHA

---

## Sentry Dashboard Features

### 1. Issues

View all errors grouped by type:
- Click on an issue to see details
- See stack trace and error context
- View user impact (how many users affected)
- Mark as resolved or ignored

### 2. Performance

Monitor slow endpoints:
- See average response times
- Identify N+1 query issues
- Find slow database queries
- Optimize bottlenecks

### 3. Releases

Track deployments:
- See which commit introduced a bug
- Compare error rates between releases
- Roll back if needed

### 4. Alerts

Set up notifications:
- Email alerts for new errors
- Slack integration for team notifications
- Custom alert rules (e.g., >100 errors/hour)
- Integration with PagerDuty for on-call

---

## Best Practices

### 1. Set Up Alerts

Configure alerts for critical errors:

1. Go to **Alerts** → **Create Alert**
2. Choose "Issues" alert type
3. Set conditions:
   - When: **A new issue is created**
   - Then: **Send notification via email**
4. Save alert rule

### 2. Use Release Tracking

Tag each deployment:

```bash
# Automatically done via RAILWAY_GIT_COMMIT_SHA
# Manual option:
export SENTRY_RELEASE=myrecoverypal@1.0.0
```

### 3. Add Context to Errors

In your code, you can add custom context:

```python
from sentry_sdk import capture_exception, set_user, set_tag

# Add user context (only if PII is acceptable)
set_user({"id": user.id, "username": user.username})

# Add custom tags
set_tag("subscription_tier", user.subscription.tier)

# Manually capture an exception
try:
    risky_operation()
except Exception as e:
    capture_exception(e)
```

### 4. Filter Noise

Ignore expected errors:

1. Go to **Settings** → **Inbound Filters**
2. Add filters for:
   - Known third-party errors
   - Browser extensions (if applicable)
   - Bot traffic

### 5. Monitor Performance

Set up performance budgets:

1. Go to **Performance**
2. Identify slow endpoints (>1 second)
3. Use Django Debug Toolbar locally to optimize
4. Re-deploy and verify improvement in Sentry

---

## Cost Management

### Free Tier Limits

- **5,000 errors per month**
- **10,000 performance units per month**
- 1 user
- 90 days data retention

### Tips to Stay Within Free Tier

1. **Filter out noise:**
   - Ignore known errors
   - Filter bot traffic
   - Don't track 404s

2. **Adjust sampling:**
   - Reduce `traces_sample_rate` to 0.05 (5%)
   - If needed, reduce `sample_rate` to 0.5 (50%)

3. **Use environments:**
   - Only enable Sentry in production
   - Don't track development/staging errors

4. **Set up quotas:**
   - Go to **Settings** → **Quotas**
   - Set max events per hour
   - Prevent accidental overage

### When to Upgrade

Consider the **Team plan ($26/month)** when you:
- Exceed 5,000 errors/month
- Need more than 1 team member
- Want longer data retention (90+ days)
- Need advanced features (custom dashboards, etc.)

---

## Troubleshooting

### Errors Not Appearing in Sentry

**Check:**
1. ✅ `SENTRY_DSN` is set in Railway environment variables
2. ✅ Application has been redeployed after setting DSN
3. ✅ DSN is correct (copy-paste error?)
4. ✅ Error actually occurred (check application logs)
5. ✅ Not in development mode (Sentry may be disabled)

**Test manually:**
```python
# In Django shell
from sentry_sdk import capture_message
capture_message("Test message from Django shell")
```

### Too Many Errors

**Solutions:**
1. Fix the underlying bugs causing errors
2. Add inbound filters to ignore noise
3. Reduce sampling rate temporarily
4. Set up rate limiting on specific error types

### Performance Monitoring Not Working

**Check:**
1. ✅ `traces_sample_rate` is > 0
2. ✅ You're making HTTP requests (not just Django shell)
3. ✅ Enough traffic to hit 10% sample rate

---

## Next Steps

### After Setup

1. ✅ **Test error tracking** - Trigger a test error and verify it appears
2. ✅ **Set up alerts** - Get notified of new issues
3. ✅ **Configure integrations** - Add Slack/email notifications
4. ✅ **Remove test endpoint** - Delete `sentry-debug` view after testing
5. ✅ **Monitor dashboard** - Check daily for first week

### Ongoing Maintenance

- **Weekly:** Review new errors and fix critical issues
- **Monthly:** Check performance metrics and optimize slow endpoints
- **Quarterly:** Review alert rules and adjust as needed

---

## Resources

- **Sentry Documentation:** https://docs.sentry.io/platforms/python/guides/django/
- **Sentry Django Guide:** https://docs.sentry.io/platforms/python/guides/django/
- **Performance Monitoring:** https://docs.sentry.io/product/performance/
- **Release Tracking:** https://docs.sentry.io/product/releases/

---

## Support

If you encounter issues with Sentry setup:

1. Check Sentry documentation: https://docs.sentry.io/
2. Sentry community forum: https://forum.sentry.io/
3. Email Sentry support: support@sentry.io (paid plans only)

---

**You're all set!** Sentry will now catch errors in production and help you maintain a stable, reliable platform for your users.
