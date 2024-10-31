from flask import request, current_app
from models import UserActivity
from app import db

def log_user_activity(user, activity_type, description=None):
    """
    Log user activity
    
    :param user: User object
    :param activity_type: String describing the type of activity
    :param description: Optional detailed description
    """
    try:
        activity = UserActivity(
            user_id=user.id,
            activity_type=activity_type,
            description=description,
            ip_address=request.remote_addr
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Error logging user activity: {str(e)}')
        db.session.rollback() 