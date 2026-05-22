-- 会议 AI 系统数据库建表脚本
-- 数据库: MySQL
-- 字符集: utf8mb4

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS meeting_ai 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE meeting_ai;

-- 创建会议记录表
CREATE TABLE IF NOT EXISTS meetings (
    -- 主键
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    -- 唯一标识
    file_id VARCHAR(64) NOT NULL UNIQUE COMMENT '文件唯一ID (UUID)',
    
    -- 会议基本信息
    meeting_name VARCHAR(255) DEFAULT NULL COMMENT '会议名称',
    original_filename VARCHAR(255) DEFAULT NULL COMMENT '原始文件名',
    meeting_type VARCHAR(20) NOT NULL DEFAULT 'batch' COMMENT '会议类型: batch-批量上传, realtime-实时转写',
    
    -- 文件路径
    audio_file_path VARCHAR(500) DEFAULT NULL COMMENT '音频文件路径',
    transcript_file_path VARCHAR(500) NOT NULL COMMENT '转写文本文件路径',
    summary_file_path VARCHAR(500) DEFAULT NULL COMMENT '会议纪要文件路径',
    
    -- 内容数据
    transcript TEXT NOT NULL COMMENT '转写文本内容',
    summary TEXT DEFAULT NULL COMMENT '会议纪要内容',
    
    -- 数据统计
    transcript_length INT NOT NULL DEFAULT 0 COMMENT '转写文本长度',
    summary_length INT DEFAULT 0 COMMENT '纪要文本长度',
    audio_duration VARCHAR(50) DEFAULT NULL COMMENT '音频时长',
    
    -- 性能指标
    asr_duration_ms INT DEFAULT NULL COMMENT 'ASR识别耗时(毫秒)',
    llm_duration_ms INT DEFAULT NULL COMMENT 'LLM生成耗时(毫秒)',
    total_duration_ms INT DEFAULT NULL COMMENT '总处理耗时(毫秒)',
    
    -- 时间戳
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'completed' COMMENT '状态: processing-处理中, completed-已完成, failed-失败',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    
    -- 索引
    INDEX idx_file_id (file_id),
    INDEX idx_created_at (created_at),
    INDEX idx_meeting_type (meeting_type),
    INDEX idx_status (status)
    
) ENGINE=InnoDB 
DEFAULT CHARSET=utf8mb4 
COLLATE=utf8mb4_unicode_ci 
COMMENT='会议记录表';

-- 显示表结构
DESCRIBE meetings;

-- 示例查询
-- SELECT * FROM meetings ORDER BY created_at DESC LIMIT 10;
-- SELECT COUNT(*) FROM meetings WHERE status = 'completed';
-- SELECT meeting_type, COUNT(*) FROM meetings GROUP BY meeting_type;
