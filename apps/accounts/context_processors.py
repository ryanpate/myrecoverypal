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
        'is_court_user': False,
        'is_free_user': True,
    }

    try:
        if request.user.is_authenticated and hasattr(request.user, 'subscription'):
            subscription = request.user.subscription
            context.update({
                'user_subscription': subscription,
                'is_premium_user': subscription.is_premium(),
                'is_court_user': subscription.is_court(),
                # Free = no active paid plan. Checking tier == 'free' let a
                # lapsed Premium/Court member (tier unchanged, status expired)
                # keep Premium-only content such as the progress analytics.
                # Active Supporters keep their current (ungated) experience.
                'is_free_user': not (subscription.is_premium() or subscription.is_supporter()),
            })
    except Exception:
        # Handle case where subscription doesn't exist
        pass

    return context
