"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Index, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Meeting(Base):
    """会议记录表"""
    __tablename__ = 'meetings'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    
    # 唯一标识
    file_id = Column(String(64), unique=True, nullable=False, index=True, comment='文件唯一ID (UUID)')
    
    # 会议基本信息
    meeting_name = Column(String(255), nullable=True, comment='会议名称')
    original_filename = Column(String(255), nullable=True, comment='原始文件名')
    meeting_type = Column(String(20), nullable=False, default='batch', comment='会议类型: batch-批量上传, realtime-实时转写')
    
    # 文件路径
    audio_file_path = Column(String(500), nullable=True, comment='音频文件路径')
    transcript_file_path = Column(String(500), nullable=False, comment='转写文本文件路径')
    summary_file_path = Column(String(500), nullable=True, comment='会议纪要文件路径')
    
    # 内容数据
    transcript = Column(Text, nullable=False, comment='转写文本内容')
    summary = Column(Text, nullable=True, comment='会议纪要内容')
    
    # 数据统计
    transcript_length = Column(Integer, nullable=False, default=0, comment='转写文本长度')
    summary_length = Column(Integer, nullable=True, default=0, comment='纪要文本长度')
    audio_duration = Column(String(50), nullable=True, comment='音频时长')
    
    # 性能指标
    asr_duration_ms = Column(Integer, nullable=True, comment='ASR识别耗时(毫秒)')
    llm_duration_ms = Column(Integer, nullable=True, comment='LLM生成耗时(毫秒)')
    total_duration_ms = Column(Integer, nullable=True, comment='总处理耗时(毫秒)')
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 状态
    status = Column(String(20), nullable=False, default='completed', comment='状态: processing-处理中, completed-已完成, failed-失败')
    error_message = Column(Text, nullable=True, comment='错误信息')
    
    # 索引
    __table_args__ = (
        Index('idx_file_id', 'file_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_meeting_type', 'meeting_type'),
        Index('idx_status', 'status'),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'meeting_name': self.meeting_name,
            'original_filename': self.original_filename,
            'meeting_type': self.meeting_type,
            'audio_file_path': self.audio_file_path,
            'transcript_file_path': self.transcript_file_path,
            'summary_file_path': self.summary_file_path,
            'transcript': self.transcript,
            'summary': self.summary,
            'transcript_length': self.transcript_length,
            'summary_length': self.summary_length,
            'audio_duration': self.audio_duration,
            'asr_duration_ms': self.asr_duration_ms,
            'llm_duration_ms': self.llm_duration_ms,
            'total_duration_ms': self.total_duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'error_message': self.error_message,
        }


def init_database(database_url: str):
    """初始化数据库"""
    from urllib.parse import urlparse
    
    # 解析数据库URL
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip('/')
    
    # 创建不带数据库名的连接来创建数据库
    base_url = f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
    
    try:
        # 尝试连接到MySQL服务器（不指定数据库）
        temp_engine = create_engine(base_url, echo=False)
        with temp_engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            if not result.fetchone():
                # 数据库不存在，创建它
                conn.execute(text(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                print(f"✓ 数据库 '{db_name}' 创建成功")
            else:
                print(f"✓ 数据库 '{db_name}' 已存在")
        temp_engine.dispose()
    except Exception as e:
        print(f"⚠ 自动创建数据库失败: {str(e)}")
        print(f"请手动执行: mysql -u root -p -e \"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\"")
        raise
    
    # 现在使用完整的数据库URL创建引擎并创建表
    engine = create_engine(database_url, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    print(f"✓ 数据库表结构创建成功")
    return engine


def get_session_factory(engine):
    """获取会话工厂"""
    return sessionmaker(bind=engine)
