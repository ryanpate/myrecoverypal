# apps/accounts/context_processors.py
"""
Context processors for making subscription data available in all templates
"""


def subscription_context(request):
    """
    Makes user subscription status available in all templates
    """
    context = {
        'user_subscription': None,
        'is_premium_user': False,
        'is_pro_user': False,
        'is_free_user': True,
    }

    try:
        if request.user.is_authenticated and hasattr(request.user, 'subscription'):
            subscription = request.user.subscription
            context.update({
                'user_subscription': subscription,
                'is_premium_user': subscription.is_premium(),
                'is_pro_user': subscription.is_pro(),
                'is_free_user': subscription.tier == 'free',
            })
    except Exception:
        # Handle case where subscription doesn't exist
        pass

    return context
