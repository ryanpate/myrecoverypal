# Push Notifications Setup Guide

## Overview

This guide explains how to set up native push notifications for MyRecoveryPal mobile apps on both Android (Firebase Cloud Messaging) and iOS (Apple Push Notification service).

## Prerequisites

- Mobile apps built and configured (see MOBILE_APP_GUIDE.md)
- Firebase account (for Android)
- Apple Developer account (for iOS)
- Django backend access

## Android Push Notifications (Firebase Cloud Messaging)

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project" or select existing project
3. Follow the setup wizard

### Step 2: Add Android App to Firebase

1. In Firebase Console, click "Add app" → Android
2. Enter package name: `com.myrecoverypal.app`
3. Download `google-services.json`
4. Place file in: `android/app/google-services.json`

### Step 3: Update Android Configuration

Add to `android/app/build.gradle`:

```gradle
plugins {
    id 'com.android.application'
    id 'com.google.gms.google-services'  // Add this line
}

dependencies {
    // Add these Firebase dependencies
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
    implementation 'com.google.firebase:firebase-analytics'
}
```

Add to `android/build.gradle`:

```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'  // Add this line
    }
}
```

Update `android/app/src/main/AndroidManifest.xml`:

```xml
<manifest>
    <!-- Add permissions -->
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.INTERNET"/>

    <application>
        <!-- Add Firebase messaging service -->
        <service
            android:name=".FirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT"/>
            </intent-filter>
        </service>

        <!-- Optional: Configure notification icon and color -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_icon"
            android:resource="@drawable/ic_notification"/>
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_color"
            android:resource="@color/notification_color"/>
    </application>
</manifest>
```

### Step 4: Get FCM Server Key

1. In Firebase Console → Project Settings → Cloud Messaging
2. Find "Server key" under Project credentials
3. Copy this key - you'll need it for Django backend

### Step 5: Update Capacitor App

In your app's TypeScript/JavaScript code (if using custom native code):

```typescript
import { PushNotifications } from '@capacitor/push-notifications';

// Request permission
PushNotifications.requestPermissions().then(result => {
  if (result.receive === 'granted') {
    // Register with FCM
    PushNotifications.register();
  }
});

// Listen for registration
PushNotifications.addListener('registration', (token) => {
  console.log('Push registration success, token: ' + token.value);
  // Send this token to your Django backend
  sendTokenToBackend(token.value);
});

// Listen for push notifications
PushNotifications.addListener('pushNotificationReceived', (notification) => {
  console.log('Push notification received: ', notification);
});

// Handle notification tap
PushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
  console.log('Push notification action performed', notification);
});
```

## iOS Push Notifications (APNs)

### Step 1: Configure App ID

1. Go to [Apple Developer Portal](https://developer.apple.com/account)
2. Certificates, Identifiers & Profiles → Identifiers
3. Find or create App ID for `com.myrecoverypal.app`
4. Enable "Push Notifications" capability
5. Click "Save"

### Step 2: Create APNs Certificate

**Option A: APNs Auth Key (Recommended)**

1. In Apple Developer Portal → Keys
2. Click + to create new key
3. Name it (e.g., "MyRecoveryPal APNs Key")
4. Enable "Apple Push Notifications service (APNs)"
5. Download the `.p8` file
6. Note the Key ID and Team ID

**Option B: APNs SSL Certificate**

1. On your Mac, open Keychain Access
2. Keychain Access → Certificate Assistant → Request Certificate from Certificate Authority
3. Enter email and name, save to disk
4. In Apple Developer Portal → Certificates
5. Create new certificate → Apple Push Notification service SSL
6. Upload the certificate request
7. Download the certificate
8. Double-click to install in Keychain

### Step 3: Configure Xcode Project

1. Open project in Xcode: `npm run cap:open:ios`
2. Select the App target
3. Go to "Signing & Capabilities"
4. Click "+ Capability"
5. Add "Push Notifications"
6. Add "Background Modes"
7. Check "Remote notifications" in Background Modes

### Step 4: Update iOS Configuration

Update `ios/App/App/Info.plist`:

```xml
<dict>
    <!-- Add these entries -->
    <key>UIBackgroundModes</key>
    <array>
        <string>remote-notification</string>
    </array>
</dict>
```

### Step 5: Request Permissions in App

The Capacitor Push Notifications plugin handles this, but you can customize:

```typescript
import { PushNotifications } from '@capacitor/push-notifications';

// Request permission
PushNotifications.requestPermissions().then(result => {
  if (result.receive === 'granted') {
    PushNotifications.register();
  } else {
    // Show alert explaining why notifications are important
  }
});

// Get device token
PushNotifications.addListener('registration', (token) => {
  console.log('Push registration success, token: ' + token.value);
  sendTokenToBackend(token.value);
});
```

## Django Backend Integration

### Step 1: Install Required Packages

```bash
pip install firebase-admin  # For Android FCM
pip install apns2          # For iOS APNs
```

Add to `requirements.txt`:
```
firebase-admin>=6.0.0
apns2>=0.7.0
```

### Step 2: Create Django App for Notifications

```bash
python manage.py startapp notifications
```

Add to `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'apps.notifications',
]
```

### Step 3: Create Models

`apps/notifications/models.py`:

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DeviceToken(models.Model):
    PLATFORM_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'token']

    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.token[:20]}..."


class PushNotification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"
```

### Step 4: Create Notification Service

`apps/notifications/services.py`:

```python
import firebase_admin
from firebase_admin import credentials, messaging
from apns2.client import APNsClient
from apns2.payload import Payload
from django.conf import settings
import os

# Initialize Firebase Admin (for Android FCM)
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

# Initialize APNs client (for iOS)
apns_client = None
if hasattr(settings, 'APNS_KEY_PATH'):
    apns_client = APNsClient(
        settings.APNS_KEY_PATH,
        use_sandbox=settings.APNS_USE_SANDBOX,
        use_alternative_port=False
    )


def send_push_notification(user, title, message, data=None):
    """
    Send push notification to all user's devices
    """
    from .models import DeviceToken

    device_tokens = DeviceToken.objects.filter(user=user, active=True)

    results = {
        'ios': {'success': 0, 'failed': 0},
        'android': {'success': 0, 'failed': 0}
    }

    for device in device_tokens:
        try:
            if device.platform == 'android':
                success = send_fcm_notification(device.token, title, message, data)
            elif device.platform == 'ios':
                success = send_apns_notification(device.token, title, message, data)

            if success:
                results[device.platform]['success'] += 1
            else:
                results[device.platform]['failed'] += 1
                device.active = False
                device.save()

        except Exception as e:
            print(f"Error sending to {device.platform}: {e}")
            results[device.platform]['failed'] += 1

    return results


def send_fcm_notification(token, title, message, data=None):
    """
    Send notification via Firebase Cloud Messaging (Android)
    """
    try:
        notification = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            data=data or {},
            token=token,
        )

        response = messaging.send(notification)
        print(f"Successfully sent FCM message: {response}")
        return True

    except Exception as e:
        print(f"FCM Error: {e}")
        return False


def send_apns_notification(token, title, message, data=None):
    """
    Send notification via Apple Push Notification service (iOS)
    """
    if not apns_client:
        print("APNs client not configured")
        return False

    try:
        payload = Payload(
            alert={
                'title': title,
                'body': message,
            },
            badge=1,
            sound='default',
            custom=data or {}
        )

        apns_client.send_notification(
            token,
            payload,
            topic=settings.APNS_TOPIC  # Your app bundle ID
        )

        print(f"Successfully sent APNs message")
        return True

    except Exception as e:
        print(f"APNs Error: {e}")
        return False
```

### Step 5: Create API Endpoints

`apps/notifications/views.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DeviceToken

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    """
    Register a device token for push notifications
    POST /api/notifications/register/
    {
        "token": "device_token_here",
        "platform": "ios" or "android"
    }
    """
    token = request.data.get('token')
    platform = request.data.get('platform')

    if not token or platform not in ['ios', 'android']:
        return Response({'error': 'Invalid data'}, status=400)

    # Create or update device token
    device_token, created = DeviceToken.objects.update_or_create(
        user=request.user,
        token=token,
        defaults={
            'platform': platform,
            'active': True
        }
    )

    return Response({
        'success': True,
        'created': created
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unregister_device_token(request):
    """
    Unregister a device token
    POST /api/notifications/unregister/
    {
        "token": "device_token_here"
    }
    """
    token = request.data.get('token')

    if not token:
        return Response({'error': 'Token required'}, status=400)

    DeviceToken.objects.filter(user=request.user, token=token).delete()

    return Response({'success': True})
```

`apps/notifications/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('register/', views.register_device_token, name='register'),
    path('unregister/', views.unregister_device_token, name='unregister'),
]
```

Add to main `urls.py`:

```python
urlpatterns = [
    # ...
    path('api/notifications/', include('apps.notifications.urls')),
]
```

### Step 6: Configure Django Settings

Add to `settings.py`:

```python
# Firebase Configuration (Android)
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-credentials.json')

# APNs Configuration (iOS)
APNS_KEY_PATH = os.path.join(BASE_DIR, 'apns-key.p8')
APNS_KEY_ID = 'YOUR_KEY_ID'
APNS_TEAM_ID = 'YOUR_TEAM_ID'
APNS_TOPIC = 'com.myrecoverypal.app'  # Your app bundle ID
APNS_USE_SANDBOX = False  # Set to True for development
```

### Step 7: Usage Examples

**Send notification when user gets a new message:**

```python
from apps.notifications.services import send_push_notification

def notify_new_message(recipient, sender, message):
    send_push_notification(
        user=recipient,
        title=f"New message from {sender.username}",
        message=message.content[:100],
        data={
            'type': 'message',
            'message_id': str(message.id),
            'sender_id': str(sender.id)
        }
    )
```

**Send notification for milestone:**

```python
def notify_milestone_achieved(user, milestone_days):
    send_push_notification(
        user=user,
        title="🎉 Milestone Achieved!",
        message=f"Congratulations on {milestone_days} days of recovery!",
        data={
            'type': 'milestone',
            'days': milestone_days
        }
    )
```

## Testing Push Notifications

### Testing Android (FCM)

1. Build and install app on device/emulator
2. App should register and get token
3. Send test notification from Firebase Console:
   - Go to Cloud Messaging
   - Click "Send test message"
   - Enter device token
   - Send notification

Or use `curl`:

```bash
curl -X POST https://fcm.googleapis.com/fcm/send \
  -H "Authorization: key=YOUR_FCM_SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "DEVICE_TOKEN",
    "notification": {
      "title": "Test Notification",
      "body": "This is a test"
    }
  }'
```

### Testing iOS (APNs)

1. Build and install app on physical device (push doesn't work on simulator)
2. App should request permission and get token
3. Use a tool like [Knuff](https://github.com/KnuffApp/Knuff) or [Pusher](https://github.com/noodlewerk/NWPusher)
4. Or use `curl` with your APNs certificate

## Troubleshooting

### Android Issues

**No token received:**
- Check `google-services.json` is in correct location
- Verify Firebase project configuration
- Check Gradle build logs for errors

**Notifications not appearing:**
- Check Android notification settings for app
- Verify FCM server key is correct
- Check device/emulator has Google Play Services

### iOS Issues

**Token not generated:**
- Must test on physical device (not simulator)
- Check App ID has Push Notifications enabled
- Verify code signing and provisioning profile

**Notifications not appearing:**
- Check device notification settings
- Verify APNs certificate/key is valid
- Ensure app is not in foreground (background only by default)
- Check APNs environment (sandbox vs production)

### General Issues

**Token not saved to backend:**
- Check API endpoint is accessible
- Verify authentication is working
- Check network connectivity

**Notifications sent but not received:**
- Verify tokens are active and valid
- Check device notification permissions
- Review server logs for errors

## Best Practices

1. **Handle permissions gracefully**
   - Request at appropriate time
   - Explain why notifications are needed
   - Provide settings to manage preferences

2. **Token management**
   - Update tokens when they change
   - Mark inactive when sending fails
   - Clean up old tokens periodically

3. **Notification content**
   - Keep titles short (< 40 chars)
   - Messages clear and actionable
   - Use data payload for app-specific info

4. **Respect user preferences**
   - Allow users to control notification types
   - Respect quiet hours
   - Don't spam with too many notifications

5. **Testing**
   - Test on real devices
   - Test both platforms
   - Test with app in foreground and background
   - Test notification tap actions

## Resources

- [Firebase Cloud Messaging Docs](https://firebase.google.com/docs/cloud-messaging)
- [Apple Push Notifications Docs](https://developer.apple.com/documentation/usernotifications)
- [Capacitor Push Notifications Plugin](https://capacitorjs.com/docs/apis/push-notifications)

---

**Note:** This guide covers the basics. For production use, consider adding:
- Notification scheduling
- Rich notifications (images, actions)
- Notification categories
- Analytics tracking
- A/B testing for notifications
