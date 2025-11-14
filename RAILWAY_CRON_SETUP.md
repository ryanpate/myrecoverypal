# Railway Cron Job Setup for Trial Expiration

This guide explains how to set up automated trial expiration on Railway.

## Automatic Trial Expiration

The `expire_trials` management command automatically downgrades users from Premium trial to Free tier when their 14-day trial period ends.

## Option 1: Railway Cron Jobs (Recommended)

Railway supports scheduled tasks through their dashboard:

### Setup Steps:

1. **Go to Railway Dashboard**
   - Open your MyRecoveryPal project
   - Click on your Django service

2. **Create a Cron Job**
   - Click "New" → "Cron Job"
   - Or use the Railway CLI: `railway run python manage.py expire_trials`

3. **Configure the Schedule**
   ```
   Name: Expire Trials
   Command: python manage.py expire_trials
   Schedule: 0 0 * * * (daily at midnight UTC)
   ```

4. **Alternative Schedules**
   - Every 6 hours: `0 */6 * * *`
   - Twice daily: `0 0,12 * * *`
   - Every hour: `0 * * * *`

## Option 2: Railway Scheduled Service

Create a separate scheduled service in Railway:

1. Add a new service to your project
2. Set the start command: `python manage.py expire_trials`
3. Configure it as a scheduled job
4. Set frequency in Railway dashboard

## Option 3: External Cron Service

Use a free external service like:

### EasyCron (Free tier available)
1. Sign up at https://www.easycron.com
2. Create new cron job
3. Set URL: `https://your-domain.com/admin/` (to keep service alive)
4. Set to run every hour
5. Add webhook to trigger: `curl https://your-railway-url.railway.app && railway run python manage.py expire_trials`

### Cron-job.org (Free)
1. Sign up at https://cron-job.org
2. Create new cron job
3. URL: Your Railway app URL (keeps dyno alive)
4. Schedule: Daily
5. Add notification webhook if needed

## Manual Execution

You can always run manually via Railway CLI:

```bash
# One-time execution
railway run python manage.py expire_trials

# Dry run to test
railway run python manage.py expire_trials --dry-run
```

## Monitoring

Check Django Admin → Subscriptions to monitor:
- Users with `status = 'trialing'`
- Users with expired `trial_end` dates
- Recent downgrades to Free tier

## Logging

The command logs all actions:
- Number of trials expired
- User details for each expiration
- Any errors encountered

Check Railway logs for output:
```
Successfully expired 5 trial subscription(s)
  - Downgraded user john_doe to free tier
  - Downgraded user jane_smith to free tier
  ...
```

## Recommended Schedule

**Daily at midnight (UTC)**: `0 0 * * *`

This ensures trials are expired promptly without running unnecessarily often.
