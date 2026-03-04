# apps/accounts/payment_views.py
"""
Payment and subscription views for Stripe integration
"""
import stripe
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import logging

from .payment_models import (
    Subscription, Transaction, PaymentMethod,
    Invoice, SubscriptionPlan
)
from .email_service import send_email

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def pricing(request):
    """
    Pricing page showing available subscription plans
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order')

    # Get user's current subscription
    user_subscription = None
    if hasattr(request.user, 'subscription'):
        user_subscription = request.user.subscription

    context = {
        'plans': plans,
        'user_subscription': user_subscription,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'accounts/pricing.html', context)


@login_required
@require_POST
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for subscription
    """
    try:
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        # Get or create Stripe customer
        subscription = None
        if hasattr(request.user, 'subscription'):
            subscription = request.user.subscription
            stripe_customer_id = subscription.stripe_customer_id
        else:
            stripe_customer_id = None

        if not stripe_customer_id:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={
                    'user_id': request.user.id,
                    'username': request.user.username,
                }
            )
            stripe_customer_id = customer.id

            # Create or update subscription record
            if not subscription:
                subscription = Subscription.objects.create(
                    user=request.user,
                    stripe_customer_id=stripe_customer_id
                )
            else:
                subscription.stripe_customer_id = stripe_customer_id
                subscription.save()

        # Check if user is still in their initial trial (no prior Stripe subscription)
        trial_kwargs = {}
        if subscription and not subscription.stripe_subscription_id:
            # First-time subscriber — give 14-day free trial on Stripe side
            trial_kwargs['subscription_data'] = {
                'trial_period_days': 14,
                'metadata': {
                    'user_id': str(request.user.id),
                    'plan_id': str(plan.id),
                    'tier': plan.tier,
                },
            }
        else:
            trial_kwargs['subscription_data'] = {
                'metadata': {
                    'user_id': str(request.user.id),
                    'plan_id': str(plan.id),
                    'tier': plan.tier,
                },
            }

        # Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri(
                reverse('accounts:payment_success')
            ) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(
                reverse('accounts:payment_canceled')
            ),
            metadata={
                'user_id': request.user.id,
                'plan_id': plan.id,
            },
            **trial_kwargs,
        )

        return JsonResponse({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })

    except Exception as e:
        logger.error(f'Checkout session creation error: {e}')
        return JsonResponse({
            'error': str(e)
        }, status=400)


@login_required
def payment_success(request):
    """
    Payment success page after Stripe Checkout
    """
    session_id = request.GET.get('session_id')

    if session_id:
        try:
            # Retrieve the session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)

            # Get subscription details
            stripe_subscription = stripe.Subscription.retrieve(session.subscription)

            # Update local subscription
            subscription = request.user.subscription
            price_id = stripe_subscription['items']['data'][0]['price']['id']

            # Determine tier from SubscriptionPlan by matching Stripe price ID
            try:
                plan = SubscriptionPlan.objects.get(stripe_price_id=price_id, is_active=True)
                subscription.tier = plan.tier
                subscription.billing_period = plan.billing_period
            except SubscriptionPlan.DoesNotExist:
                subscription.tier = 'premium'  # Fallback

            subscription.status = stripe_subscription.status
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.stripe_price_id = price_id
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_end, tz=timezone.utc
            )
            subscription.save()

            messages.success(
                request,
                'Payment successful! Your subscription is now active. Welcome to Premium!'
            )

        except Exception as e:
            logger.error(f'Error processing payment success: {e}')
            messages.warning(
                request,
                'Payment completed, but there was an issue updating your subscription. '
                'Please contact support if you don\'t see your benefits.'
            )

    context = {
        'session_id': session_id,
    }
    return render(request, 'accounts/payment_success.html', context)


@login_required
def payment_canceled(request):
    """
    Payment canceled page
    """
    messages.info(request, 'Payment was canceled. You can try again anytime!')
    return render(request, 'accounts/payment_canceled.html')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint for handling events
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    if not webhook_secret:
        logger.warning('Stripe webhook secret not configured')
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        # Invalid payload
        logger.error('Invalid webhook payload')
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        logger.error('Invalid webhook signature')
        return HttpResponse(status=400)

    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']

    logger.info(f'Received Stripe webhook: {event_type}')

    try:
        if event_type == 'checkout.session.completed':
            handle_checkout_session_completed(event_data)

        elif event_type == 'invoice.paid':
            handle_invoice_paid(event_data)

        elif event_type == 'invoice.payment_failed':
            handle_invoice_payment_failed(event_data)

        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(event_data)

        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(event_data)

        elif event_type == 'customer.subscription.trial_will_end':
            handle_trial_will_end(event_data)

    except Exception as e:
        logger.error(f'Error handling webhook {event_type}: {e}')
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """Handle successful checkout session"""
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')

    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)

        # Update subscription with Stripe subscription ID
        if subscription_id:
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            subscription.stripe_subscription_id = subscription_id
            subscription.status = stripe_subscription.status
            subscription.subscription_source = 'stripe'

            # Set tier from subscription metadata or price ID
            metadata = stripe_subscription.get('metadata', {})
            tier = metadata.get('tier', '')
            if tier in ['premium', 'pro']:
                subscription.tier = tier
            else:
                # Fallback: look up from SubscriptionPlan
                price_id = stripe_subscription['items']['data'][0]['price']['id']
                try:
                    plan = SubscriptionPlan.objects.get(stripe_price_id=price_id, is_active=True)
                    subscription.tier = plan.tier
                except SubscriptionPlan.DoesNotExist:
                    subscription.tier = 'premium'

            subscription.current_period_start = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_end, tz=timezone.utc
            )
            subscription.save()

        logger.info(f'Checkout completed for subscription {subscription.id}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found for customer {customer_id}')


def handle_invoice_paid(invoice):
    """Handle successful invoice payment"""
    customer_id = invoice.get('customer')
    subscription_id = invoice.get('subscription')
    amount_paid = Decimal(str(invoice.get('amount_paid', 0))) / 100  # Convert from cents

    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)

        # Create transaction record
        Transaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            transaction_type='subscription',
            status='succeeded',
            amount=amount_paid,
            currency=invoice.get('currency', 'usd').upper(),
            stripe_invoice_id=invoice.get('id'),
            stripe_charge_id=invoice.get('charge'),
            description=f'Subscription payment - {subscription.get_tier_display()}',
        )

        # Update subscription status
        subscription.status = 'active'
        subscription.save()

        logger.info(f'Invoice paid for subscription {subscription.id}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found for customer {customer_id}')


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    customer_id = invoice.get('customer')
    amount_due = Decimal(str(invoice.get('amount_due', 0))) / 100

    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)

        # Create failed transaction record
        Transaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            transaction_type='subscription',
            status='failed',
            amount=amount_due,
            currency=invoice.get('currency', 'usd').upper(),
            stripe_invoice_id=invoice.get('id'),
            description=f'Failed subscription payment - {subscription.get_tier_display()}',
            failure_reason=invoice.get('last_payment_error', {}).get('message', 'Payment failed'),
        )

        # Update subscription status
        subscription.status = 'past_due'
        subscription.save()

        logger.warning(f'Payment failed for subscription {subscription.id}')

        # Notify user of payment failure
        try:
            user = subscription.user
            send_email(
                subject='Action Required: Payment Failed - MyRecoveryPal',
                plain_message=(
                    f'Hi {user.first_name or user.username},\n\n'
                    'We were unable to process your subscription payment. '
                    'Please update your payment method to continue enjoying Premium features.\n\n'
                    'Visit https://www.myrecoverypal.com/accounts/subscription/ to update your payment info.\n\n'
                    'Your recovery journey matters to us,\nThe MyRecoveryPal Team'
                ),
                html_message=_billing_email_html(
                    user,
                    'Payment Failed',
                    'We were unable to process your subscription payment. '
                    'Please update your payment method to continue enjoying Premium features.',
                    'Update Payment Method',
                    'https://www.myrecoverypal.com/accounts/subscription/'
                ),
                recipient_email=user.email,
            )
        except Exception as email_err:
            logger.error(f'Failed to send payment failure email: {email_err}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found for customer {customer_id}')


def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates"""
    subscription_id = stripe_subscription.get('id')

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)

        # Update subscription details
        subscription.status = stripe_subscription.get('status')
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            stripe_subscription.get('current_period_start'), tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription.get('current_period_end'), tz=timezone.utc
        )

        # Check if subscription was canceled
        if stripe_subscription.get('cancel_at_period_end'):
            subscription.canceled_at = timezone.now()

        subscription.save()

        logger.info(f'Subscription updated: {subscription.id}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found: {subscription_id}')


def handle_subscription_deleted(stripe_subscription):
    """Handle subscription cancellation"""
    subscription_id = stripe_subscription.get('id')

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)

        # Downgrade to free tier
        subscription.tier = 'free'
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()

        logger.info(f'Subscription canceled: {subscription.id}')

        # Notify user of cancellation
        try:
            user = subscription.user
            send_email(
                subject='Your Premium Subscription Has Ended - MyRecoveryPal',
                plain_message=(
                    f'Hi {user.first_name or user.username},\n\n'
                    'Your Premium subscription has ended. You still have full access to our '
                    'free features including the social feed, groups, and daily check-ins.\n\n'
                    'If you\'d like to resubscribe, visit https://www.myrecoverypal.com/accounts/pricing/\n\n'
                    'Your recovery journey continues,\nThe MyRecoveryPal Team'
                ),
                html_message=_billing_email_html(
                    user,
                    'Subscription Ended',
                    'Your Premium subscription has ended. You still have full access to our '
                    'free features including the social feed, groups, and daily check-ins.',
                    'Resubscribe to Premium',
                    'https://www.myrecoverypal.com/accounts/pricing/'
                ),
                recipient_email=user.email,
            )
        except Exception as email_err:
            logger.error(f'Failed to send cancellation email: {email_err}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found: {subscription_id}')


def handle_trial_will_end(stripe_subscription):
    """Handle trial ending soon notification"""
    subscription_id = stripe_subscription.get('id')

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)

        logger.info(f'Trial ending soon for subscription {subscription.id}')

        # Notify user that trial is ending in 3 days
        try:
            user = subscription.user
            send_email(
                subject='Your Free Trial Ends Soon - MyRecoveryPal',
                plain_message=(
                    f'Hi {user.first_name or user.username},\n\n'
                    'Your 14-day free trial of MyRecoveryPal Premium ends in 3 days. '
                    'After that, your card on file will be charged.\n\n'
                    'To keep Premium: No action needed - your subscription continues automatically.\n'
                    'To cancel: Visit https://www.myrecoverypal.com/accounts/subscription/\n\n'
                    'Thank you for being part of the recovery community,\nThe MyRecoveryPal Team'
                ),
                html_message=_billing_email_html(
                    user,
                    'Your Trial Ends in 3 Days',
                    'Your 14-day free trial of MyRecoveryPal Premium ends in 3 days. '
                    'After that, your card on file will be charged automatically. '
                    'No action needed to keep Premium &mdash; or manage your subscription below.',
                    'Manage Subscription',
                    'https://www.myrecoverypal.com/accounts/subscription/'
                ),
                recipient_email=user.email,
            )
        except Exception as email_err:
            logger.error(f'Failed to send trial ending email: {email_err}')

    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found: {subscription_id}')


@login_required
def subscription_management(request):
    """
    Subscription management page
    View current subscription, billing history, manage payment methods
    """
    subscription = None
    transactions = []
    invoices = []

    if hasattr(request.user, 'subscription'):
        subscription = request.user.subscription
        transactions = Transaction.objects.filter(
            user=request.user,
            status='succeeded'
        )[:10]
        invoices = Invoice.objects.filter(user=request.user)[:10]

    context = {
        'subscription': subscription,
        'transactions': transactions,
        'invoices': invoices,
    }
    return render(request, 'accounts/subscription_management.html', context)


@login_required
@require_POST
def cancel_subscription(request):
    """
    Cancel user's subscription
    """
    try:
        subscription = request.user.subscription

        if not subscription.stripe_subscription_id:
            messages.error(request, 'No active subscription found.')
            return redirect('accounts:subscription_management')

        # Cancel at period end (don't cancel immediately)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        subscription.canceled_at = timezone.now()
        subscription.save()

        messages.success(
            request,
            f'Your subscription has been scheduled for cancellation. '
            f'You\'ll continue to have access until {subscription.current_period_end.strftime("%B %d, %Y")}.'
        )

    except Exception as e:
        logger.error(f'Error canceling subscription: {e}')
        messages.error(request, 'There was an error canceling your subscription. Please try again.')

    return redirect('accounts:subscription_management')


@login_required
@require_POST
def reactivate_subscription(request):
    """
    Reactivate a canceled subscription
    """
    try:
        subscription = request.user.subscription

        if not subscription.stripe_subscription_id:
            messages.error(request, 'No subscription found.')
            return redirect('accounts:subscription_management')

        # Reactivate by removing cancel_at_period_end
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )

        subscription.canceled_at = None
        subscription.save()

        messages.success(request, 'Your subscription has been reactivated!')

    except Exception as e:
        logger.error(f'Error reactivating subscription: {e}')
        messages.error(request, 'There was an error reactivating your subscription. Please try again.')

    return redirect('accounts:subscription_management')


@login_required
@require_POST
def ios_subscription_sync(request):
    """
    Sync iOS in-app purchase subscription state from RevenueCat.
    Called by capacitor-iap.js after purchase/restore.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    is_premium = data.get('is_premium', False)
    product_id = data.get('product_id')
    expires_date = data.get('expires_date')

    # Get or create subscription record
    subscription, created = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'tier': 'free', 'status': 'active'}
    )

    # Only update if this is an Apple-sourced subscription
    # Don't overwrite active Stripe subscriptions
    if subscription.subscription_source == 'stripe' and subscription.is_premium():
        logger.info(f'Skipping iOS sync for user {request.user.id} — active Stripe subscription')
        return JsonResponse({'status': 'skipped', 'reason': 'active_stripe_subscription'})

    if is_premium:
        subscription.tier = 'premium'
        subscription.status = 'active'
        subscription.subscription_source = 'apple'
        if expires_date:
            try:
                from dateutil.parser import parse as parse_date
                subscription.current_period_end = parse_date(expires_date)
            except (ValueError, ImportError):
                pass
        subscription.save()
        logger.info(f'iOS subscription activated for user {request.user.id}')
    else:
        # Only downgrade if the subscription was Apple-sourced
        if subscription.subscription_source == 'apple':
            subscription.tier = 'free'
            subscription.status = 'canceled'
            subscription.save()
            logger.info(f'iOS subscription expired for user {request.user.id}')

    return JsonResponse({'status': 'ok', 'is_premium': is_premium})


@login_required
def create_customer_portal_session(request):
    """
    Create Stripe Customer Portal session for managing payment methods
    """
    try:
        subscription = request.user.subscription

        if not subscription.stripe_customer_id:
            messages.error(request, 'No customer account found.')
            return redirect('accounts:subscription_management')

        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=request.build_absolute_uri(
                reverse('accounts:subscription_management')
            ),
        )

        return redirect(portal_session.url)

    except Exception as e:
        logger.error(f'Error creating portal session: {e}')
        messages.error(request, 'There was an error accessing the billing portal. Please try again.')
        return redirect('accounts:subscription_management')


def _billing_email_html(user, heading, body_text, cta_label, cta_url):
    """Generate a simple branded HTML email for billing notifications."""
    name = user.first_name or user.username
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;background:#f4f4f4;">
<div style="background:white;border-radius:15px;padding:40px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
  <div style="text-align:center;margin-bottom:30px;">
    <span style="font-size:32px;font-weight:700;background:linear-gradient(135deg,#1e4d8b 0%,#4db8e8 60%,#52b788 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">MyRecoveryPal</span>
  </div>
  <h2 style="color:#1e4d8b;margin:0 0 15px;">{heading}</h2>
  <p>Hi {name},</p>
  <p>{body_text}</p>
  <div style="text-align:center;margin:30px 0;">
    <a href="{cta_url}" style="display:inline-block;background:linear-gradient(135deg,#1e4d8b,#4db8e8);color:white;padding:12px 30px;border-radius:25px;text-decoration:none;font-weight:600;">{cta_label}</a>
  </div>
  <p style="color:#666;font-size:14px;">Your recovery journey matters to us.<br>The MyRecoveryPal Team</p>
</div>
</body></html>'''
