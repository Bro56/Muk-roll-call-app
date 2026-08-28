"""
app_utils/notifications.py
Deduplicated notification engine for the Smart Attendance System.
"""

from extensions import db, socketio
from models import Notification
from sqlalchemy import and_
from datetime import datetime, timedelta


def notify_user(recipient_id, title, message, notification_type="info", link=None, dedup_window_minutes=30):
    """
    Send a notification to a single user with deduplication.

    If an unread notification with the same type and title exists within 
    the deduplication window, no new notification is created.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=dedup_window_minutes)

    existing = Notification.query.filter(
        and_(
            Notification.recipient_id == recipient_id,
            Notification.notification_type == notification_type,
            Notification.title == title,
            Notification.read == False,
            Notification.created_at >= cutoff
        )
    ).first()

    if existing:
        return existing

    notif = Notification(
        recipient_id=recipient_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        created_at=datetime.utcnow(),
        read=False
    )
    db.session.add(notif)
    db.session.commit()

    try:
        socketio.emit('new_notification', {
            'id': notif.id,
            'title': title,
            'message': message,
            'type': notification_type,
            'link': link,
            'created_at': notif.created_at.isoformat()
        }, room=f'user_{recipient_id}')
    except Exception:
        pass

    return notif


def notify_admins(title, message, notification_type="warning", link=None, exclude_admin_id=None):
    """Send a notification to all admin users with deduplication per admin."""
    from models import User

    admins = User.query.filter_by(role='admin').all()
    sent_notifications = []

    for admin in admins:
        if exclude_admin_id and admin.id == exclude_admin_id:
            continue
        notif = notify_user(
            recipient_id=admin.id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            dedup_window_minutes=30
        )
        sent_notifications.append(notif)

    return sent_notifications


def notify_lecturer(lecturer_id, title, message, notification_type="info", link=None):
    """Convenience wrapper for lecturer-specific notifications."""
    return notify_user(
        recipient_id=lecturer_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )


def mark_notification_read(notification_id, user_id):
    """Mark a specific notification as read, verifying ownership."""
    notif = Notification.query.filter_by(
        id=notification_id,
        recipient_id=user_id
    ).first()

    if notif:
        notif.read = True
        db.session.commit()
        return True
    return False


def get_unread_count(user_id):
    """Get count of unread notifications for a user."""
    return Notification.query.filter_by(
        recipient_id=user_id,
        read=False
    ).count()


def get_recent_notifications(user_id, limit=20, include_read=False):
    """Get recent notifications for a user, newest first."""
    query = Notification.query.filter_by(recipient_id=user_id)
    if not include_read:
        query = query.filter_by(read=False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()