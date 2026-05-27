"""会议访问权限判断"""
from datetime import datetime, timedelta

from db.models import Meeting, User

ROOT_MEETING_VIEW_DAYS = 3


def can_access_meeting(viewer: User, meeting: Meeting, owner: User | None) -> bool:
    """判断用户是否有权查看某条会议记录"""
    if meeting.user_id == viewer.id:
        return True

    if viewer.is_root():
        return True

    owner_role = owner.role if owner else None

    if owner_role == 'root':
        if viewer.role != 'admin' or not viewer.can_view_root_meetings:
            return False
        cutoff = datetime.now() - timedelta(days=ROOT_MEETING_VIEW_DAYS)
        return meeting.created_at is not None and meeting.created_at >= cutoff

    if viewer.role == 'admin' or viewer.can_view_all:
        return True

    return False
