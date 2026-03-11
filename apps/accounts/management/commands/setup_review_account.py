"""
Populate the Apple App Store review account with realistic demo data.

Usage:
    python manage.py setup_review_account

Creates: profile data, sobriety date, check-ins, journal entries,
social posts, group memberships, coach conversation, follows,
and a Premium subscription.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the applereview account with demo data for App Store review'

    REVIEW_USERNAME = 'applereview'
    EXPIRED_USERNAME = 'applereview2'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=self.REVIEW_USERNAME)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'User "{self.REVIEW_USERNAME}" not found. Create the account first.'
            ))
            return

        self.stdout.write(f'Setting up review account: {user.username} (id={user.id})')

        self._setup_profile(user)
        self._setup_subscription(user)
        self._create_checkins(user)
        self._create_journal_entries(user)
        self._create_social_posts(user)
        self._join_groups(user)
        self._follow_users(user)
        self._create_coach_conversation(user)

        self.stdout.write(self.style.SUCCESS('Review account setup complete!'))

        # Set up the expired-trial account for Apple review (Guideline 2.1)
        self._setup_expired_account()

    def _setup_expired_account(self):
        """Create/update a second demo account with an expired trial subscription."""
        self.stdout.write('\n--- Setting up expired-trial review account ---')

        user, created = User.objects.get_or_create(
            username=self.EXPIRED_USERNAME,
            defaults={
                'email': 'review2@myrecoverypal.com',
            }
        )
        if created:
            user.set_password('applereview2')
            self.stdout.write(f'  Created user: {self.EXPIRED_USERNAME}')
        else:
            self.stdout.write(f'  User already exists: {self.EXPIRED_USERNAME}')

        user.first_name = 'Jordan'
        user.last_name = 'T.'
        user.bio = 'Taking it one day at a time. Grateful for every morning I wake up clear-headed.'
        user.sobriety_date = date(2025, 12, 1)
        user.recovery_goals = 'Build healthy habits and stay connected with supportive people.'
        user.recovery_stage = 'early'
        user.interests = 'fitness,meditation,journaling'
        user.is_profile_public = True
        user.show_sobriety_date = True
        user.allow_messages = True
        user.has_completed_onboarding = True
        user.location = 'United States'
        user.save()

        # Create an expired trial subscription
        from apps.accounts.payment_models import Subscription
        sub, _ = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'tier': 'free',
                'status': 'expired',
                'subscription_source': 'manual',
                'current_period_start': timezone.now() - timedelta(days=21),
                'current_period_end': timezone.now() - timedelta(days=7),
                'trial_end': timezone.now() - timedelta(days=7),
            }
        )
        sub.tier = 'free'
        sub.status = 'expired'
        sub.subscription_source = 'manual'
        sub.current_period_start = timezone.now() - timedelta(days=21)
        sub.current_period_end = timezone.now() - timedelta(days=7)
        sub.trial_end = timezone.now() - timedelta(days=7)
        sub.save()

        # Add some check-ins so the account looks real
        from apps.accounts.models import DailyCheckIn
        for days_ago in [1, 2, 3]:
            DailyCheckIn.objects.get_or_create(
                user=user,
                date=date.today() - timedelta(days=days_ago),
                defaults={
                    'mood': random.randint(5, 8),
                    'energy_level': random.randint(5, 7),
                    'craving_level': random.randint(2, 5),
                    'gratitude': 'Grateful for another sober day.',
                    'is_shared': False,
                }
            )

        # Use up the 3 free AI Coach trial messages
        from apps.accounts.models import RecoveryCoachSession, CoachMessage
        session, _ = RecoveryCoachSession.objects.get_or_create(
            user=user, is_active=True, defaults={'title': 'Recovery Chat'}
        )
        if not CoachMessage.objects.filter(session=session).exists():
            trial_messages = [
                {'role': 'user', 'content': 'I need some help with cravings.'},
                {'role': 'assistant', 'content': 'I\'m here for you. Let\'s talk about what you\'re feeling right now.'},
                {'role': 'user', 'content': 'It\'s been tough this week at work.'},
                {'role': 'assistant', 'content': 'Work stress is one of the most common triggers. Let\'s explore some coping strategies.'},
                {'role': 'user', 'content': 'What can I do when I feel the urge?'},
                {'role': 'assistant', 'content': 'There are several techniques: deep breathing, calling your sponsor, or going for a walk. Which sounds most accessible right now?'},
            ]
            for msg in trial_messages:
                CoachMessage.objects.create(
                    session=session,
                    role=msg['role'],
                    content=msg['content'],
                    tokens_used=random.randint(30, 100),
                )

        self.stdout.write(self.style.SUCCESS(
            f'  Expired-trial account ready: {self.EXPIRED_USERNAME} / applereview2\n'
            f'  - Trial expired 7 days ago\n'
            f'  - 3 AI Coach trial messages used\n'
            f'  - Will see upgrade prompts when using AI Coach or premium features'
        ))

    def _setup_profile(self, user):
        self.stdout.write('  Setting up profile...')
        user.first_name = 'Alex'
        user.last_name = 'R.'
        user.bio = (
            'In recovery since 2025. Grateful for every sober day. '
            'This community helps me stay connected and accountable. '
            'One day at a time.'
        )
        user.sobriety_date = date(2025, 6, 1)  # ~9 months sober
        user.recovery_goals = 'Stay connected with my recovery community. Practice daily gratitude. Help others who are just starting out.'
        user.recovery_stage = 'maintaining'
        user.interests = 'meditation,gratitude,fitness,journaling,mindfulness'
        user.is_profile_public = True
        user.show_sobriety_date = True
        user.allow_messages = True
        user.has_completed_onboarding = True
        user.is_sponsor = False
        user.location = 'United States'
        user.save()
        days = (date.today() - user.sobriety_date).days
        self.stdout.write(f'    Sobriety date: {user.sobriety_date} ({days} days)')

    def _setup_subscription(self, user):
        from apps.accounts.payment_models import Subscription
        self.stdout.write('  Setting up Premium subscription...')
        sub, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'tier': 'premium',
                'status': 'active',
                'subscription_source': 'manual',
                'current_period_start': timezone.now() - timedelta(days=7),
                'current_period_end': timezone.now() + timedelta(days=365),
            }
        )
        if not created:
            sub.tier = 'premium'
            sub.status = 'active'
            sub.subscription_source = 'manual'
            sub.current_period_start = timezone.now() - timedelta(days=7)
            sub.current_period_end = timezone.now() + timedelta(days=365)
            sub.save()
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'    {action} Premium subscription')

    def _create_checkins(self, user):
        from apps.accounts.models import DailyCheckIn
        self.stdout.write('  Creating daily check-ins...')

        checkins = [
            {
                'days_ago': 0,
                'mood': 8,
                'energy_level': 7,
                'craving_level': 2,
                'gratitude': 'Grateful for this community and the support I get every day.',
            },
            {
                'days_ago': 1,
                'mood': 7,
                'energy_level': 6,
                'craving_level': 3,
                'gratitude': 'Had a great conversation with my sponsor today.',
            },
            {
                'days_ago': 2,
                'mood': 6,
                'energy_level': 5,
                'craving_level': 4,
                'gratitude': 'Went for a long walk and felt at peace with the world.',
            },
            {
                'days_ago': 3,
                'mood': 9,
                'energy_level': 8,
                'craving_level': 1,
                'gratitude': 'Celebrated 9 months sober with friends who understand.',
            },
            {
                'days_ago': 5,
                'mood': 7,
                'energy_level': 7,
                'craving_level': 2,
                'gratitude': 'Morning meditation is becoming a real anchor in my routine.',
            },
        ]

        count = 0
        for ci in checkins:
            checkin_date = date.today() - timedelta(days=ci['days_ago'])
            obj, created = DailyCheckIn.objects.get_or_create(
                user=user,
                date=checkin_date,
                defaults={
                    'mood': ci['mood'],
                    'energy_level': ci['energy_level'],
                    'craving_level': ci['craving_level'],
                    'gratitude': ci['gratitude'],
                    'is_shared': ci['days_ago'] in (0, 3),
                }
            )
            if created:
                # Backdate the created_at
                DailyCheckIn.objects.filter(pk=obj.pk).update(
                    created_at=timezone.now() - timedelta(days=ci['days_ago'], hours=random.randint(8, 18))
                )
                count += 1
        self.stdout.write(f'    Created {count} check-ins')

    def _create_journal_entries(self, user):
        from apps.journal.models import JournalEntry, JournalStreak
        self.stdout.write('  Creating journal entries...')

        entries = [
            {
                'days_ago': 1,
                'title': 'Reflecting on How Far I\'ve Come',
                'content': (
                    'Nine months ago I couldn\'t imagine going a single day without drinking. '
                    'Today I woke up clear-headed, went for a run, and actually enjoyed my morning coffee '
                    'without needing anything else.\n\n'
                    'The early days were brutal. I remember lying awake at 2 AM, hands shaking, '
                    'telling myself "just one more day." Now those days feel like a different lifetime.\n\n'
                    'What helped most: this community. Having people who actually understand what '
                    'it\'s like to rebuild your life from scratch. No judgment, just support.\n\n'
                    'I\'m not where I want to be yet, but I\'m so far from where I was. And that\'s enough.'
                ),
                'mood_rating': 8,
                'tags': 'gratitude,milestone,reflection',
                'cravings_today': False,
            },
            {
                'days_ago': 4,
                'title': 'Tough Day, But I Got Through It',
                'content': (
                    'Work was stressful today. Old me would have headed straight to the bar after a day like this. '
                    'Instead I called my sponsor, went to a meeting, and came home to write this.\n\n'
                    'The cravings were real today. Not gonna lie. Around 5 PM when everyone was talking about '
                    'happy hour plans, I felt that familiar pull. But I played the tape forward \u2014 '
                    'I know exactly where that first drink leads.\n\n'
                    'Talked to Anchor (the AI coach on here) about some coping strategies and it actually helped '
                    'me reframe the situation. Sometimes you just need to talk it out, even at midnight.\n\n'
                    'Tomorrow is a new day. I\'m going to bed sober, and that\'s a win.'
                ),
                'mood_rating': 5,
                'tags': 'cravings,coping,honesty',
                'cravings_today': True,
                'craving_intensity': 6,
            },
            {
                'days_ago': 8,
                'title': 'Morning Routine That Changed Everything',
                'content': (
                    'Someone in my recovery group shared their morning routine and I decided to try it:\n\n'
                    '1. Wake up, no phone for 30 minutes\n'
                    '2. 10-minute meditation (just breathing, nothing fancy)\n'
                    '3. Write 3 things I\'m grateful for\n'
                    '4. Quick walk around the block\n\n'
                    'I\'ve been doing this for two weeks now and the difference is real. '
                    'My mornings used to be filled with anxiety and regret. Now they feel like a fresh start.\n\n'
                    'The gratitude practice especially \u2014 it rewires how I see the day. '
                    'Even on tough days, I can find three good things. Today: '
                    'coffee, sunshine, and a text from an old friend checking in.'
                ),
                'mood_rating': 7,
                'tags': 'routine,meditation,gratitude,wellness',
                'cravings_today': False,
            },
        ]

        count = 0
        for entry_data in entries:
            title = entry_data['title']
            if not JournalEntry.objects.filter(user=user, title=title).exists():
                entry = JournalEntry.objects.create(
                    user=user,
                    title=title,
                    content=entry_data['content'],
                    mood_rating=entry_data['mood_rating'],
                    tags=entry_data['tags'],
                    cravings_today=entry_data['cravings_today'],
                    craving_intensity=entry_data.get('craving_intensity'),
                )
                JournalEntry.objects.filter(pk=entry.pk).update(
                    created_at=timezone.now() - timedelta(days=entry_data['days_ago'], hours=random.randint(19, 22))
                )
                count += 1

        # Set up a journal streak
        streak, _ = JournalStreak.objects.get_or_create(user=user)
        streak.current_streak = 4
        streak.longest_streak = 12
        streak.total_entries = JournalEntry.objects.filter(user=user).count()
        streak.last_entry_date = date.today() - timedelta(days=1)
        streak.save()

        self.stdout.write(f'    Created {count} journal entries')

    def _create_social_posts(self, user):
        from apps.accounts.models import SocialPost
        self.stdout.write('  Creating social posts...')

        posts = [
            {
                'days_ago': 0,
                'content': (
                    '9 months sober today. Never thought I\'d be able to say that. '
                    'To everyone just starting out: it gets easier. Not every day, but overall the trend '
                    'is up. You\'re stronger than you think. \U0001f4aa\n\n'
                    '#recovery #sobriety #milestone #9months'
                ),
            },
            {
                'days_ago': 3,
                'content': (
                    'Started using the daily check-in feature and it\'s become part of my routine now. '
                    'There\'s something powerful about tracking your mood every day \u2014 you start to see '
                    'patterns you never noticed before.\n\n'
                    'Today\'s mood: 8/10 \u2728\nCravings: Low \u2705\nGrateful for: This community'
                ),
            },
            {
                'days_ago': 7,
                'content': (
                    'Had a rough day at work but instead of reaching for a drink, I opened this app '
                    'and talked to Anchor. Sometimes you just need someone (or something) to listen '
                    'without judgment at 11 PM.\n\n'
                    'Recovery isn\'t linear. Bad days don\'t erase good ones. \U0001f49a'
                ),
            },
        ]

        count = 0
        for post_data in posts:
            content_prefix = post_data['content'][:50]
            if not SocialPost.objects.filter(author=user, content__startswith=content_prefix).exists():
                post = SocialPost.objects.create(
                    author=user,
                    content=post_data['content'],
                    visibility='public',
                )
                SocialPost.objects.filter(pk=post.pk).update(
                    created_at=timezone.now() - timedelta(days=post_data['days_ago'], hours=random.randint(10, 20))
                )
                count += 1
        self.stdout.write(f'    Created {count} social posts')

    def _join_groups(self, user):
        from apps.accounts.models import RecoveryGroup, GroupMembership
        self.stdout.write('  Joining groups...')

        # Join existing public groups
        public_groups = RecoveryGroup.objects.filter(privacy_level='public')[:3]
        count = 0
        for group in public_groups:
            _, created = GroupMembership.objects.get_or_create(
                user=user,
                group=group,
                defaults={'status': 'active'}
            )
            if created:
                count += 1
                self.stdout.write(f'    Joined: {group.name}')

        if count == 0 and not public_groups.exists():
            # Create a couple of groups if none exist
            for name, gtype in [
                ('Alcohol Recovery Support', 'addiction_type'),
                ('Daily Meditation & Mindfulness', 'interest'),
            ]:
                group, g_created = RecoveryGroup.objects.get_or_create(
                    name=name,
                    defaults={
                        'creator': user,
                        'group_type': gtype,
                        'privacy_level': 'public',
                        'description': f'A supportive space for everyone interested in {name.lower()}.',
                        'max_members': 100,
                    }
                )
                if g_created:
                    GroupMembership.objects.get_or_create(
                        user=user, group=group,
                        defaults={'status': 'admin'}
                    )
                    count += 1
                    self.stdout.write(f'    Created & joined: {group.name}')

        self.stdout.write(f'    Joined {count} groups')

    def _follow_users(self, user):
        from apps.accounts.models import UserConnection
        self.stdout.write('  Following users...')

        # Follow up to 5 active users (not self)
        targets = User.objects.filter(
            is_active=True,
            is_profile_public=True,
        ).exclude(id=user.id).order_by('-last_login')[:5]

        count = 0
        for target in targets:
            _, created = UserConnection.objects.get_or_create(
                follower=user,
                following=target,
                defaults={'connection_type': 'follow'}
            )
            if created:
                count += 1
                # Create mutual follow for some users
                if random.random() > 0.4:
                    UserConnection.objects.get_or_create(
                        follower=target,
                        following=user,
                        defaults={'connection_type': 'follow'}
                    )

        self.stdout.write(f'    Following {count} users')

    def _create_coach_conversation(self, user):
        from apps.accounts.models import RecoveryCoachSession, CoachMessage
        self.stdout.write('  Creating AI Coach conversation...')

        session, created = RecoveryCoachSession.objects.get_or_create(
            user=user,
            is_active=True,
            defaults={'title': 'Recovery Support'}
        )

        if CoachMessage.objects.filter(session=session).exists():
            self.stdout.write('    Coach conversation already exists, skipping')
            return

        messages = [
            {
                'role': 'user',
                'content': 'I\'m having a tough evening. Work was really stressful and I keep thinking about having a drink.',
                'minutes_ago': 45,
            },
            {
                'role': 'assistant',
                'content': (
                    'I hear you, and I want you to know that reaching out right now instead of reaching for a drink '
                    'is a really strong move. That takes real courage.\n\n'
                    'Let\'s take this one step at a time. First, can you take a few deep breaths with me? '
                    'Inhale for 4 counts, hold for 4, exhale for 6. Sometimes just slowing down the body '
                    'helps slow down the mind.\n\n'
                    'You mentioned work stress \u2014 what happened today that\'s weighing on you?'
                ),
                'minutes_ago': 44,
            },
            {
                'role': 'user',
                'content': 'My manager called me out in front of the whole team for something that wasn\'t even my fault. I felt humiliated. The old me would be at a bar right now.',
                'minutes_ago': 40,
            },
            {
                'role': 'assistant',
                'content': (
                    'That sounds really frustrating and unfair. Being called out publicly \u2014 especially for '
                    'something that wasn\'t your mistake \u2014 would make anyone upset. Your feelings are completely valid.\n\n'
                    'But notice what you just said: "The old me would be at a bar right now." You\'re not that person anymore. '
                    'You\'re 9 months into building a new version of yourself, and right now you\'re proving that '
                    'by being here instead of there.\n\n'
                    'Here are a few things that might help tonight:\n\n'
                    '\u2022 **Write it out** \u2014 Sometimes journaling about what happened helps process the anger '
                    'so it doesn\'t stay stuck inside\n'
                    '\u2022 **Move your body** \u2014 Even a 15-minute walk can shift your energy\n'
                    '\u2022 **Call someone** \u2014 Your sponsor, a recovery pal, or anyone who gets it\n\n'
                    'Which of these feels most doable right now?'
                ),
                'minutes_ago': 38,
            },
            {
                'role': 'user',
                'content': 'I think I\'ll journal about it. And maybe go for a walk first to clear my head. Thanks, Anchor. I needed this.',
                'minutes_ago': 35,
            },
            {
                'role': 'assistant',
                'content': (
                    'That\'s a great plan. Walk first to move the energy, then journal to process it. '
                    'You\'ve got a solid toolkit now \u2014 and you\'re using it.\n\n'
                    'Remember: one bad day at work doesn\'t undo 9 months of hard work. '
                    'You\'re going to wake up tomorrow clear-headed, and that\'s something to be proud of.\n\n'
                    'I\'m here anytime you need to talk. You\'ve got this. \U0001f49a'
                ),
                'minutes_ago': 34,
            },
        ]

        for msg in messages:
            CoachMessage.objects.create(
                session=session,
                role=msg['role'],
                content=msg['content'],
                tokens_used=random.randint(50, 200),
            )
            # Backdate
            CoachMessage.objects.filter(
                session=session, content=msg['content']
            ).update(
                created_at=timezone.now() - timedelta(minutes=msg['minutes_ago'])
            )

        self.stdout.write(f'    Created conversation with {len(messages)} messages')
