"""
app_utils/audit.py
Immutable audit trail logger for the Smart Attendance System.
Every security-critical action is logged with actor, action, entity, and IP.
"""

from extensions import db
from models import AuditLog
from datetime import datetime
from flask import request


def log_audit(actor_id, action, entity_type, entity_id, details=None):
    """
    Create an immutable audit log entry.

    Args:
        actor_id: User ID who performed the action (or None for system)
        action: Short action string, e.g. 'user.delete', 'class_rep.approve'
        entity_type: Model name, e.g. 'User', 'ClassRep', 'LecturerActivationCode'
        entity_id: Primary key of affected entity
        details: Optional human-readable details dict or string
    """
    try:
        ip_address = request.remote_addr if request else None
    except RuntimeError:
        ip_address = None  # Outside request context

    if isinstance(details, dict):
        details_str = str(details)
    else:
        details_str = details or ""

    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details_str,
        ip_address=ip_address,
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()
    return log


def get_audit_logs(entity_type=None, entity_id=None, actor_id=None, limit=100):
    """Query audit logs with optional filters."""
    query = AuditLog.query

    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    if actor_id:
        query = query.filter_by(actor_id=actor_id)

    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()