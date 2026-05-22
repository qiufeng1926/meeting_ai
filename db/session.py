"""
数据库会话管理
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session
from db.models import init_database, get_session_factory, Meeting
from config.config import database_url
from utils.logger import get_logger

logger = get_logger("database")

# 初始化数据库引擎和会话工厂
engine = init_database(database_url)
SessionFactory = get_session_factory(engine)


@contextmanager
def get_db_session() -> Session:
    """获取数据库会话的上下文管理器"""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败，已回滚: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()


def save_meeting_to_db(meeting_data: dict) -> Meeting:
    """
    保存会议记录到数据库
    
    Args:
        meeting_data: 会议数据字典
        
    Returns:
        Meeting: 保存的会议记录对象
    """
    with get_db_session() as session:
        meeting = Meeting(
            file_id=meeting_data['file_id'],
            meeting_name=meeting_data.get('meeting_name'),
            original_filename=meeting_data.get('original_filename'),
            meeting_type=meeting_data.get('meeting_type', 'batch'),
            audio_file_path=meeting_data.get('audio_file_path'),
            transcript_file_path=meeting_data['transcript_file_path'],
            summary_file_path=meeting_data.get('summary_file_path'),
            transcript=meeting_data['transcript'],
            summary=meeting_data.get('summary'),
            transcript_length=meeting_data.get('transcript_length', len(meeting_data['transcript'])),
            summary_length=meeting_data.get('summary_length', len(meeting_data.get('summary', '')) if meeting_data.get('summary') else 0),
            audio_duration=meeting_data.get('audio_duration'),
            asr_duration_ms=meeting_data.get('asr_duration_ms'),
            llm_duration_ms=meeting_data.get('llm_duration_ms'),
            total_duration_ms=meeting_data.get('total_duration_ms'),
            status=meeting_data.get('status', 'completed'),
            error_message=meeting_data.get('error_message'),
        )
        session.add(meeting)
        logger.info(f"会议记录已保存到数据库: file_id={meeting_data['file_id']}")
        return meeting


def update_meeting_status(file_id: str, status: str, error_message: str = None):
    """
    更新会议状态
    
    Args:
        file_id: 文件ID
        status: 新状态
        error_message: 错误信息（可选）
    """
    with get_db_session() as session:
        meeting = session.query(Meeting).filter(Meeting.file_id == file_id).first()
        if meeting:
            meeting.status = status
            if error_message:
                meeting.error_message = error_message
            logger.info(f"会议状态已更新: file_id={file_id}, status={status}")
        else:
            logger.warning(f"未找到会议记录: file_id={file_id}")


def get_meeting_by_file_id(file_id: str) -> Meeting:
    """
    根据file_id获取会议记录
    
    Args:
        file_id: 文件ID
        
    Returns:
        Meeting: 会议记录对象，不存在则返回None
    """
    with get_db_session() as session:
        meeting = session.query(Meeting).filter(Meeting.file_id == file_id).first()
        return meeting


def get_all_meetings(limit: int = 100, offset: int = 0, start_date: str = None, end_date: str = None) -> list:
    """
    获取所有会议记录（分页，支持日期筛选）
    
    Args:
        limit: 每页数量
        offset: 偏移量
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        
    Returns:
        list: 会议记录字典列表
    """
    with get_db_session() as session:
        query = session.query(Meeting)
        
        # 添加日期筛选条件
        if start_date:
            try:
                from datetime import datetime as dt
                start_dt = dt.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Meeting.created_at >= start_dt)
            except ValueError:
                logger.warning(f"无效的开始日期格式: {start_date}")
        
        if end_date:
            try:
                from datetime import datetime as dt, timedelta
                end_dt = dt.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Meeting.created_at < end_dt)
            except ValueError:
                logger.warning(f"无效的结束日期格式: {end_date}")
        
        meetings = query.order_by(Meeting.created_at.desc()).limit(limit).offset(offset).all()
        
        # 在会话关闭前转换为字典
        return [meeting.to_dict() for meeting in meetings]


def delete_meeting(file_id: str) -> bool:
    """
    删除会议记录
    
    Args:
        file_id: 文件ID
        
    Returns:
        bool: 是否删除成功
    """
    with get_db_session() as session:
        meeting = session.query(Meeting).filter(Meeting.file_id == file_id).first()
        if meeting:
            session.delete(meeting)
            logger.info(f"会议记录已删除: file_id={file_id}")
            return True
        else:
            logger.warning(f"未找到会议记录: file_id={file_id}")
            return False

