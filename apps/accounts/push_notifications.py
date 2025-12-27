"""
Push Notification Service for MyRecoveryPal

This module provides push notification triggers for key user events.
Currently logs notifications and creates in-app Notification records.
Can be extended with Firebase FCM / Apple APNs when mobile infrastructure is ready.

Usage:
    from apps.accounts.push_notifications import PushNotificationService

    PushNotificationService.notify_new_follower(follower, followed_user)
    PushNotificationService.notify_new_comment(commenter, post)
    PushNotificationService.notify_new_like(liker, post)
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


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
        Send push notification to user.
        Currently logs the notification. Extend with FCM/APNs integration.
        """
        if not cls._should_send_push(recipient):
            return False

        template = cls.NOTIFICATION_TEMPLATES.get(notification_type, {})
        sender_name = cls._get_sender_name(sender)

        title = template.get('title', 'MyRecoveryPal')
        body = template.get('body', 'You have a new notification').format(sender=sender_name)

        # Log the push notification (for debugging and when push isn't configured)
        logger.info(f"[PUSH] To: {recipient.email} | Type: {notification_type} | "
                   f"Title: {title} | Body: {body}")

        # TODO: When Firebase/APNs is configured, add actual push here:
        # from .services import send_fcm_notification, send_apns_notification
        # device_tokens = DeviceToken.objects.filter(user=recipient, active=True)
        # for token in device_tokens:
        #     if token.platform == 'android':
        #         send_fcm_notification(token.token, title, body, data)
        #     elif token.platform == 'ios':
        #         send_apns_notification(token.token, title, body, data)

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
