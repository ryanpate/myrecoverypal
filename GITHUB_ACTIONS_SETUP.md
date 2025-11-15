# GitHub Actions Setup for Automated Trial Expiration

This guide explains how to set up automated trial expiration using GitHub Actions instead of Railway cron jobs.

## Overview

The `.github/workflows/expire_trials.yml` workflow automatically runs the `expire_trials` management command daily at midnight UTC to downgrade expired trial subscriptions from Premium to Free tier.

**How it works:**
- Uses Railway CLI with a project-scoped token (`RAILWAY_TOKEN`)
- Runs the Django management command via `railway run`
- Project token automatically targets your MyRecoveryPal project
- Executes daily at midnight UTC (configurable)

## Setup Instructions

### Step 1: Get Your Railway Project Token

**IMPORTANT:** You need a **project token**, not an account token. Project tokens are specific to your MyRecoveryPal project.

1. Go to [Railway Dashboard](https://railway.app/)
2. Click on your **MyRecoveryPal** project
3. Click on the **Settings** tab
4. Scroll down to the **Tokens** section
5. Click **Create Token** (or **New Token**)
6. Give it a name like "GitHub Actions - Trial Expiration"
7. Copy the token immediately (it will only be shown once!)

**Note:** This is different from account tokens found in Account Settings. Project tokens are scoped to a specific project and are required for CI/CD workflows.

### Step 2: Add Railway Token to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/ryanpate/myrecoverypal`
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter:
   - **Name:** `RAILWAY_TOKEN`
   - **Secret:** Paste the project token from Step 1
6. Click **Add secret**

You should now see `RAILWAY_TOKEN` in your secrets list.

**Important:** Make sure you're using a **project token** (from your project's Settings → Tokens), not an account token. Project tokens are already scoped to your MyRecoveryPal project, so you don't need to specify a project ID.

### Step 3: Verify Workflow is Enabled

1. In your GitHub repository, go to the **Actions** tab
2. You should see "Expire Trial Subscriptions" in the workflows list
3. If you see a message about workflows being disabled, click **Enable workflows**

### Step 4: Test the Workflow Manually

Before waiting for the scheduled run, test it manually:

1. Go to **Actions** tab
2. Click on **Expire Trial Subscriptions** workflow
3. Click **Run workflow** button (on the right side)
4. Select the branch: `claude/review-recovery-website-016PNzhU73p1xzvRzTxqnjNk` (or your main branch)
5. Click **Run workflow**
6. Watch the workflow run and check for any errors
7. Review the logs to see if trials were expired

### Step 5: Verify It's Working

After the workflow runs (either manually or on schedule):

1. Check the **Actions** tab to see the workflow run history
2. Click on a completed run to see the logs
3. Look for output like:
   ```
   Successfully expired 5 trial subscription(s)
     - Downgraded user john_doe to free tier
     - Downgraded user jane_smith to free tier
   ```
4. Verify in Django Admin → Subscriptions that expired trials were downgraded

## Schedule

The workflow runs automatically:
- **Daily at midnight UTC** (`0 0 * * *`)
- Can also be **triggered manually** anytime via GitHub Actions tab

## Monitoring

### Check Workflow Status

1. Go to repository **Actions** tab
2. Filter by workflow: "Expire Trial Subscriptions"
3. Green checkmark = successful run
4. Red X = failed run (click to see error logs)

### Email Notifications

GitHub will email you if a workflow fails. To configure notifications:

1. Go to GitHub Settings → Notifications
2. Under "Actions", choose notification preferences

## Troubleshooting

### Workflow Fails with "Project Token not found" or "Authentication Failed"

**Problem:** Using wrong token type or invalid token

**Solution:**
1. **Verify you're using a PROJECT token, not an account token**
   - Project tokens: Project Settings → Tokens (✅ Correct)
   - Account tokens: Account Settings → Tokens (❌ Wrong)
2. Delete the old `RAILWAY_TOKEN` secret in GitHub if it was an account token
3. Generate a new project token from MyRecoveryPal project settings
4. Update the `RAILWAY_TOKEN` secret in GitHub with the new project token
5. Remove `RAILWAY_PROJECT_ID` secret if it exists (not needed with project tokens)
6. Re-run the workflow

### Workflow Runs But Doesn't Expire Trials

**Problem:** Command executes but doesn't find expired trials

**Solution:**
1. Verify trials actually exist and are expired (check Django Admin)
2. Run manually with `--dry-run` to test: `railway run python manage.py expire_trials --dry-run`
3. Check Railway deployment logs for any errors

### No Trials Being Expired (Expected Behavior)

If the workflow runs successfully but shows "No expired trials found", this is normal when:
- No trial periods have ended yet
- All users are on paid plans
- Trials were already expired in a previous run

## Manual Execution

You can always run the command manually via Railway CLI locally:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Run the command
railway run python manage.py expire_trials

# Dry run to see what would be expired
railway run python manage.py expire_trials --dry-run
```

## Changing the Schedule

To change when the workflow runs, edit `.github/workflows/expire_trials.yml`:

```yaml
on:
  schedule:
    # Change this cron expression
    - cron: '0 0 * * *'  # Daily at midnight UTC
```

**Common schedules:**
- Every 6 hours: `0 */6 * * *`
- Twice daily: `0 0,12 * * *`
- Every hour: `0 * * * *`
- Weekly on Monday: `0 0 * * 1`

After changing, commit and push to GitHub. The new schedule takes effect immediately.

## Cost

GitHub Actions is **free** for public repositories and includes:
- 2,000 minutes/month for private repos (free tier)
- This workflow uses ~1-2 minutes per run
- Daily runs = ~30-60 minutes/month (well within free tier)

## Security Notes

- Never commit your Railway token to the repository
- Always use GitHub Secrets for sensitive data
- Rotate your Railway token periodically (every 90 days recommended)
- Use a token with minimal permissions (only access to MyRecoveryPal project)

## Alternative: Keep Railway Cron

If Railway adds cron job support in the future or you upgrade to a plan with cron:

1. Disable this GitHub Actions workflow (delete or rename the file)
2. Follow the instructions in `RAILWAY_CRON_SETUP.md`
3. Railway's native cron may be more reliable as it runs in the same environment

## Questions or Issues?

- Check workflow logs in GitHub Actions tab
- Review Railway deployment logs
- Test locally with `python manage.py expire_trials --dry-run`
- Ensure your Railway project is running and accessible
