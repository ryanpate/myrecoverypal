"""
Push Notification Service for MyRecoveryPal

This module provides push notification triggers for key user events.
Sends push notifications via Firebase Cloud Messaging (Android) and
Apple Push Notification service (iOS).

Usage:
    from apps.accounts.push_notifications import PushNotificationService

    PushNotificationService.notify_new_follower(follower, followed_user)
    PushNotificationService.notify_new_comment(commenter, post)
    PushNotificationService.notify_new_like(liker, post)
"""

import logging
import os
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

# Firebase Admin SDK initialization (lazy loading)
_firebase_app = None


def _get_firebase_app():
    """
    Lazily initialize Firebase Admin SDK.
    Returns None if not configured.
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    firebase_creds_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    if not firebase_creds_path or not os.path.exists(firebase_creds_path):
        logger.debug("Firebase credentials not configured - push notifications disabled")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_creds_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            _firebase_app = firebase_admin.get_app()

        return _firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")
        return None


def send_fcm_notification(token, title, body, data=None):
    """
    Send push notification via Firebase Cloud Messaging (Android/Web).

    Args:
        token: Device FCM token
        title: Notification title
        body: Notification body message
        data: Optional dict of additional data

    Returns:
        bool: True if sent successfully, False otherwise
    """
    app = _get_firebase_app()
    if not app:
        logger.debug(f"FCM not configured - would send: {title}")
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},  # FCM requires string values
            token=token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#52b788',
                    sound='default',
                ),
            ),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    icon='/static/images/favicon_192.png',
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f"FCM notification sent successfully: {response}")
        return True

    except Exception as e:
        error_str = str(e)
        # Check for invalid/unregistered token errors
        if 'UNREGISTERED' in error_str or 'INVALID' in error_str:
            logger.warning(f"FCM token invalid/unregistered: {token[:20]}...")
            return False
        logger.error(f"FCM send error: {e}")
        return False


def _get_apns_auth_token():
    """
    Generate JWT auth token for APNs.
    Tokens are valid for 1 hour, so we cache them.
    """
    import time
    import jwt

    apns_key_path = getattr(settings, 'APNS_KEY_PATH', None)
    apns_key_id = getattr(settings, 'APNS_KEY_ID', None)
    apns_team_id = getattr(settings, 'APNS_TEAM_ID', None)

    if not all([apns_key_path, apns_key_id, apns_team_id]):
        return None

    if not os.path.exists(apns_key_path):
        return None

    try:
        with open(apns_key_path, 'r') as f:
            auth_key = f.read()

        token = jwt.encode(
            {
                'iss': apns_team_id,
                'iat': int(time.time()),
            },
            auth_key,
            algorithm='ES256',
            headers={
                'alg': 'ES256',
                'kid': apns_key_id,
            }
        )
        return token
    except Exception as e:
        logger.error(f"Failed to generate APNs auth token: {e}")
        return None


def send_apns_notification(token, title, body, data=None):
    """
    Send push notification via Apple Push Notification service (iOS).
    Uses HTTP/2 with JWT authentication.

    Args:
        token: Device APNs token
        title: Notification title
        body: Notification body message
        data: Optional dict of additional data

    Returns:
        bool: True if sent successfully, False otherwise
    """
    import json

    # Check if APNs is configured
    apns_key_path = getattr(settings, 'APNS_KEY_PATH', None)
    apns_key_id = getattr(settings, 'APNS_KEY_ID', None)
    apns_team_id = getattr(settings, 'APNS_TEAM_ID', None)
    apns_topic = getattr(settings, 'APNS_TOPIC', 'com.myrecoverypal.app')

    if not all([apns_key_path, apns_key_id, apns_team_id]):
        logger.debug(f"APNs not configured - would send: {title}")
        return False

    if not os.path.exists(apns_key_path):
        logger.warning(f"APNs key file not found: {apns_key_path}")
        return False

    # Get auth token
    auth_token = _get_apns_auth_token()
    if not auth_token:
        logger.error("Failed to get APNs auth token")
        return False

    try:
        import httpx

        # Determine environment
        use_sandbox = getattr(settings, 'APNS_USE_SANDBOX', settings.DEBUG)
        if use_sandbox:
            apns_host = "https://api.sandbox.push.apple.com"
        else:
            apns_host = "https://api.push.apple.com"

        # Build payload
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "badge": 1,
                "sound": "default",
            }
        }
        # Add custom data
        if data:
            payload.update(data)

        # Send request via HTTP/2
        url = f"{apns_host}/3/device/{token}"
        headers = {
            "authorization": f"bearer {auth_token}",
            "apns-topic": apns_topic,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }

        with httpx.Client(http2=True, timeout=30.0) as client:
            response = client.post(
                url,
                headers=headers,
                content=json.dumps(payload),
            )

        if response.status_code == 200:
            logger.info(f"APNs notification sent successfully to {token[:20]}...")
            return True
        else:
            error_body = response.text
            logger.warning(f"APNs error {response.status_code}: {error_body}")

            # Check for invalid token errors
            if response.status_code in (400, 410):
                if 'BadDeviceToken' in error_body or 'Unregistered' in error_body:
                    logger.warning(f"APNs token invalid: {token[:20]}...")
            return False

    except Exception as e:
        logger.error(f"APNs send error: {e}")
        return False


def send_push_to_user(user, title, body, data=None):
    """
    Send push notification to all of a user's registered devices.

    Args:
        user: User model instance
        title: Notification title
        body: Notification body message
        data: Optional dict of additional data

    Returns:
        dict: Results with success/failure counts per platform
    """
    from .models import DeviceToken

    results = {
        'android': {'sent': 0, 'failed': 0},
        'ios': {'sent': 0, 'failed': 0},
        'web': {'sent': 0, 'failed': 0},
    }

    device_tokens = DeviceToken.objects.filter(user=user, active=True)

    for device in device_tokens:
        success = False

        if device.platform == 'android':
            success = send_fcm_notification(device.token, title, body, data)
        elif device.platform == 'ios':
            success = send_apns_notification(device.token, title, body, data)
        elif device.platform == 'web':
            success = send_fcm_notification(device.token, title, body, data)

        if success:
            results[device.platform]['sent'] += 1
            device.mark_used()
        else:
            results[device.platform]['failed'] += 1
            # Deactivate invalid tokens
            if not success:
                device.deactivate()
                logger.info(f"Deactivated invalid token for {user.username}")

    return results


class PushNotificationService:
    """
    Centralized push notification service.
    Handles creating in-app notifications and (when configured) push notifications.
    """

    # Notification type mapping to user-friendly messages
    NOTIFICATION_TEMPLATES = {
        'follow': {
            'title': 'New Follower!',
            'body': '{sender} started following you',
            'icon': '/static/images/favicon_192.png',
        },
        'like': {
            'title': 'New Like!',
            'body': '{sender} liked your post',
            'icon': '/static/images/favicon_192.png',
        },
        'comment': {
            'title': 'New Comment!',
            'body': '{sender} commented on your post',
            'icon': '/static/images/favicon_192.png',
        },
        'message': {
            'title': 'New Message!',
            'body': '{sender} sent you a message',
            'icon': '/static/images/favicon_192.png',
        },
        'pal_request': {
            'title': 'Recovery Pal Request!',
            'body': '{sender} wants to be your Recovery Pal',
            'icon': '/static/images/favicon_192.png',
        },
        'pal_accepted': {
            'title': 'Pal Request Accepted!',
            'body': '{sender} accepted your Recovery Pal request',
            'icon': '/static/images/favicon_192.png',
        },
        'sponsor_request': {
            'title': 'Sponsor Request!',
            'body': '{sender} wants you to be their sponsor',
            'icon': '/static/images/favicon_192.png',
        },
        'sponsor_accepted': {
            'title': 'Sponsor Request Accepted!',
            'body': '{sender} accepted your sponsor request',
            'icon': '/static/images/favicon_192.png',
        },
        'milestone': {
            'title': 'Milestone Celebration!',
            'body': '{sender} achieved a new milestone',
            'icon': '/static/images/favicon_192.png',
        },
        'group_invite': {
            'title': 'Group Invitation!',
            'body': "You've been invited to join a group",
            'icon': '/static/images/favicon_192.png',
        },
        'group_post': {
            'title': 'New Group Post!',
            'body': 'New post in your group',
            'icon': '/static/images/favicon_192.png',
        },
        'group_comment': {
            'title': 'New Group Comment!',
            'body': 'Someone commented in your group',
            'icon': '/static/images/favicon_192.png',
        },
        'group_join': {
            'title': 'New Member!',
            'body': '{sender} joined your group',
            'icon': '/static/images/favicon_192.png',
        },
        'challenge_invite': {
            'title': 'Challenge Invitation!',
            'body': "You've been invited to a challenge",
            'icon': '/static/images/favicon_192.png',
        },
        'meeting_reminder': {
            'title': 'Meeting Reminder',
            'body': '{meeting_name} starts in 30 minutes',
            'icon': '/static/images/favicon_192.png',
        },
        'pal_nudge': {
            'title': 'Check on Your Recovery Pal',
            'body': '{pal_name} could use your support',
            'icon': '/static/images/favicon_192.png',
        },
        'pal_nudge_inactive': {
            'title': 'Your Recovery Pal Misses You',
            'body': '{pal_name} is thinking of you - time for a check-in?',
            'icon': '/static/images/favicon_192.png',
        },
    }

    @classmethod
    def _get_sender_name(cls, sender):
        """Get display name for sender"""
        if not sender:
            return 'Someone'
        return sender.first_name or sender.username

    @classmethod
    def _create_in_app_notification(cls, recipient, sender, notification_type,
                                     content_object=None, message=None, url=None):
        """Create an in-app notification record"""
        from .models import Notification

        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            content_object=content_object,
            message=message or '',
            url=url or '',
        )

    @classmethod
    def _should_send_push(cls, user):
        """Check if user should receive push notifications"""
        # For now, always return True for users with email_notifications enabled
        # Later, add a separate push_notifications field
        return getattr(user, 'email_notifications', True)

    @classmethod
    def _send_push(cls, recipient, notification_type, sender=None, data=None):
        """
        Send push notification to user via FCM (Android/Web) and APNs (iOS).
        Falls back to logging if push services are not configured.
        """
        if not cls._should_send_push(recipient):
            return False

        template = cls.NOTIFICATION_TEMPLATES.get(notification_type, {})
        sender_name = cls._get_sender_name(sender)

        title = template.get('title', 'MyRecoveryPal')
        body = template.get('body', 'You have a new notification').format(sender=sender_name)

        # Add notification type to data payload
        push_data = data or {}
        push_data['notification_type'] = notification_type

        # Log the push notification (always, for debugging)
        logger.info(f"[PUSH] To: {recipient.email} | Type: {notification_type} | "
                   f"Title: {title} | Body: {body}")

        # Send actual push notifications to all user's devices
        results = send_push_to_user(recipient, title, body, push_data)

        # Log results
        total_sent = sum(r['sent'] for r in results.values())
        total_failed = sum(r['failed'] for r in results.values())
        if total_sent > 0 or total_failed > 0:
            logger.info(f"[PUSH RESULT] {recipient.email}: sent={total_sent}, failed={total_failed}")

        return True

    # ========================================
    # Public Notification Methods
    # ========================================

    @classmethod
    def notify_new_follower(cls, follower, followed_user):
        """Notify user when someone follows them"""
        if follower == followed_user:
            return None

        notification = cls._create_in_app_notification(
            recipient=followed_user,
            sender=follower,
            notification_type='follow',
            message=f"{cls._get_sender_name(follower)} started following you",
            url=f"/accounts/profile/{follower.username}/"
        )

        cls._send_push(
            recipient=followed_user,
            notification_type='follow',
            sender=follower,
            data={'follower_id': str(follower.id), 'type': 'follow'}
        )

        return notification

    @classmethod
    def notify_new_like(cls, liker, post):
        """Notify user when someone likes their post"""
        if liker == post.user:
            return None

        notification = cls._create_in_app_notification(
            recipient=post.user,
            sender=liker,
            notification_type='like',
            content_object=post,
            message=f"{cls._get_sender_name(liker)} liked your post",
            url=f"/accounts/social-feed/"
        )

        cls._send_push(
            recipient=post.user,
            notification_type='like',
            sender=liker,
            data={'post_id': str(post.id), 'type': 'like'}
        )

        return notification

    @classmethod
    def notify_new_comment(cls, commenter, post, comment=None):
        """Notify user when someone comments on their post"""
        if commenter == post.user:
            return None

        comment_preview = ''
        if comment and hasattr(comment, 'content'):
            comment_preview = comment.content[:50] + ('...' if len(comment.content) > 50 else '')

        notification = cls._create_in_app_notification(
            recipient=post.user,
            sender=commenter,
            notification_type='comment',
            content_object=comment or post,
            message=f"{cls._get_sender_name(commenter)} commented: {comment_preview}" if comment_preview else f"{cls._get_sender_name(commenter)} commented on your post",
            url=f"/accounts/social-feed/"
        )

        cls._send_push(
            recipient=post.user,
            notification_type='comment',
            sender=commenter,
            data={'post_id': str(post.id), 'type': 'comment'}
        )

        return notification

    @classmethod
    def notify_new_message(cls, sender, recipient, message=None):
        """Notify user when they receive a new message"""
        if sender == recipient:
            return None

        notification = cls._create_in_app_notification(
            recipient=recipient,
            sender=sender,
            notification_type='message',
            content_object=message,
            message=f"{cls._get_sender_name(sender)} sent you a message",
            url=f"/accounts/messages/"
        )

        cls._send_push(
            recipient=recipient,
            notification_type='message',
            sender=sender,
            data={'sender_id': str(sender.id), 'type': 'message'}
        )

        return notification

    @classmethod
    def notify_pal_request(cls, sender, recipient, pal_request=None):
        """Notify user when someone sends them a recovery pal request"""
        notification = cls._create_in_app_notification(
            recipient=recipient,
            sender=sender,
            notification_type='pal_request',
            content_object=pal_request,
            message=f"{cls._get_sender_name(sender)} wants to be your Recovery Pal",
            url=f"/accounts/recovery-pals/"
        )

        cls._send_push(
            recipient=recipient,
            notification_type='pal_request',
            sender=sender,
            data={'type': 'pal_request'}
        )

        return notification

    @classmethod
    def notify_pal_accepted(cls, accepter, requester, pal_relationship=None):
        """Notify user when their recovery pal request is accepted"""
        notification = cls._create_in_app_notification(
            recipient=requester,
            sender=accepter,
            notification_type='pal_accepted',
            content_object=pal_relationship,
            message=f"{cls._get_sender_name(accepter)} accepted your Recovery Pal request!",
            url=f"/accounts/profile/{accepter.username}/"
        )

        cls._send_push(
            recipient=requester,
            notification_type='pal_accepted',
            sender=accepter,
            data={'type': 'pal_accepted'}
        )

        return notification

    @classmethod
    def notify_sponsor_request(cls, sender, recipient, sponsor_request=None):
        """Notify user when someone sends them a sponsor request"""
        notification = cls._create_in_app_notification(
            recipient=recipient,
            sender=sender,
            notification_type='sponsor_request',
            content_object=sponsor_request,
            message=f"{cls._get_sender_name(sender)} wants you to be their sponsor",
            url=f"/accounts/sponsors/"
        )

        cls._send_push(
            recipient=recipient,
            notification_type='sponsor_request',
            sender=sender,
            data={'type': 'sponsor_request'}
        )

        return notification

    @classmethod
    def notify_sponsor_accepted(cls, accepter, requester, sponsor_relationship=None):
        """Notify user when their sponsor request is accepted"""
        notification = cls._create_in_app_notification(
            recipient=requester,
            sender=accepter,
            notification_type='sponsor_accepted',
            content_object=sponsor_relationship,
            message=f"{cls._get_sender_name(accepter)} accepted your sponsor request!",
            url=f"/accounts/profile/{accepter.username}/"
        )

        cls._send_push(
            recipient=requester,
            notification_type='sponsor_accepted',
            sender=accepter,
            data={'type': 'sponsor_accepted'}
        )

        return notification

    @classmethod
    def notify_group_join(cls, new_member, group):
        """Notify group creator when someone joins their group"""
        if new_member == group.creator:
            return None

        notification = cls._create_in_app_notification(
            recipient=group.creator,
            sender=new_member,
            notification_type='group_join',
            content_object=group,
            message=f"{cls._get_sender_name(new_member)} joined {group.name}",
            url=f"/accounts/groups/{group.id}/"
        )

        cls._send_push(
            recipient=group.creator,
            notification_type='group_join',
            sender=new_member,
            data={'group_id': str(group.id), 'type': 'group_join'}
        )

        return notification

    @classmethod
    def notify_group_post(cls, author, group, post, recipients=None):
        """Notify group members when there's a new post"""
        from .models import GroupMembership

        if recipients is None:
            # Get all active members except the author
            recipients = [
                m.user for m in GroupMembership.objects.filter(
                    group=group,
                    status__in=['active', 'moderator', 'admin']
                ).exclude(user=author).select_related('user')
            ]

        notifications = []
        for recipient in recipients:
            notification = cls._create_in_app_notification(
                recipient=recipient,
                sender=author,
                notification_type='group_post',
                content_object=post,
                message=f"New post in {group.name}",
                url=f"/accounts/groups/{group.id}/"
            )
            notifications.append(notification)

            cls._send_push(
                recipient=recipient,
                notification_type='group_post',
                sender=author,
                data={'group_id': str(group.id), 'post_id': str(post.id), 'type': 'group_post'}
            )

        return notifications

    @classmethod
    def notify_meeting_reminder(cls, user, meeting):
        """Notify user about an upcoming meeting they've bookmarked"""
        from .models import Notification

        meeting_name = meeting.name or meeting.group or 'Your meeting'

        notification = Notification.objects.create(
            recipient=user,
            sender=None,
            notification_type='meeting_reminder',
            message=f"{meeting_name} starts in 30 minutes",
            url=f"/support/meetings/{meeting.slug}/"
        )

        # Send push with custom template
        if cls._should_send_push(user):
            template = cls.NOTIFICATION_TEMPLATES.get('meeting_reminder', {})
            title = template.get('title', 'Meeting Reminder')
            body = f"{meeting_name} starts in 30 minutes"

            logger.info(f"[PUSH] To: {user.email} | Type: meeting_reminder | "
                       f"Title: {title} | Body: {body}")

        return notification

    @classmethod
    def notify_pal_nudge_inactive(cls, inactive_user, active_pal, days_inactive):
        """
        Notify an inactive user that their Recovery Pal is thinking of them.
        Sent when user hasn't checked in for 3+ days.
        """
        from .models import Notification

        pal_name = cls._get_sender_name(active_pal)

        notification = Notification.objects.create(
            recipient=inactive_user,
            sender=active_pal,
            notification_type='pal_nudge',
            title='Your Recovery Pal Misses You',
            message=f"{pal_name} is thinking of you. It's been {days_inactive} days since your last check-in.",
            link='/accounts/daily-checkin/'
        )

        # Send push notification
        if cls._should_send_push(inactive_user):
            template = cls.NOTIFICATION_TEMPLATES.get('pal_nudge_inactive', {})
            title = template.get('title', 'Your Recovery Pal Misses You')
            body = f"{pal_name} is thinking of you - time for a check-in?"

            logger.info(f"[PUSH] To: {inactive_user.email} | Type: pal_nudge_inactive | "
                       f"Title: {title} | Body: {body}")

        return notification

    @classmethod
    def notify_pal_nudge_active(cls, active_pal, inactive_user, days_inactive):
        """
        Notify an active pal to reach out to their inactive Recovery Pal.
        Sent when their pal hasn't checked in for 3+ days.
        """
        from .models import Notification

        pal_name = cls._get_sender_name(inactive_user)

        notification = Notification.objects.create(
            recipient=active_pal,
            sender=inactive_user,
            notification_type='pal_nudge',
            title='Check on Your Recovery Pal',
            message=f"{pal_name} hasn't checked in for {days_inactive} days. Send them some support!",
            link=f'/accounts/send-message/{inactive_user.username}/'
        )

        # Send push notification
        if cls._should_send_push(active_pal):
            template = cls.NOTIFICATION_TEMPLATES.get('pal_nudge', {})
            title = template.get('title', 'Check on Your Recovery Pal')
            body = f"{pal_name} could use your support"

            logger.info(f"[PUSH] To: {active_pal.email} | Type: pal_nudge | "
                       f"Title: {title} | Body: {body}")

        return notification
