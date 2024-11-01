from flask import request
from models import UserActivity, db

def log_user_activity(user, activity_type, description):
    """Log user activity with IP address"""
    activity = UserActivity(
        user_id=user.id,
        activity_type=activity_type,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()
