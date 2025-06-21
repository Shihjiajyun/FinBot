-- ====================================================
-- 10-K Filing Items GPT Summary Table Creation Script
-- ====================================================
-- 此腳本創建用於存儲 GPT 總結後的 10-K 檔案內容的資料表
-- 與原始 ten_k_filings 表形成一對一關聯

USE finbot_db;

-- 創建 GPT 摘要資料表
CREATE TABLE IF NOT EXISTS ten_k_filings_summary (
    -- 基本識別欄位
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'GPT摘要表主鍵',
    original_filing_id INT NOT NULL COMMENT '關聯到原始 ten_k_filings 表的 ID',
    
    -- 基本資訊欄位（從原表複製，便於查詢）
    file_name VARCHAR(255) NOT NULL COMMENT '檔案名稱',
    company_name VARCHAR(255) NOT NULL COMMENT '公司名稱',
    report_date DATE NOT NULL COMMENT '報告期間結束日期',
    
    -- GPT 摘要處理資訊
    summary_model VARCHAR(50) DEFAULT 'gpt-4' COMMENT '使用的 GPT 模型版本',
    summary_completed_at TIMESTAMP NULL COMMENT 'GPT 摘要完成時間',
    processing_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '摘要處理狀態',
    processing_notes TEXT NULL COMMENT '處理過程中的備註或錯誤訊息',
    
    -- 各 Item GPT 摘要內容
    item_1_summary TEXT NULL COMMENT 'Item 1: Business - GPT 摘要（含附錄支持數據）',
    item_1a_summary TEXT NULL COMMENT 'Item 1A: Risk Factors - GPT 摘要',
    item_1b_summary TEXT NULL COMMENT 'Item 1B: Unresolved Staff Comments - GPT 摘要',
    item_2_summary TEXT NULL COMMENT 'Item 2: Properties - GPT 摘要（含附錄支持數據）',
    item_3_summary TEXT NULL COMMENT 'Item 3: Legal Proceedings - GPT 摘要',
    item_4_summary TEXT NULL COMMENT 'Item 4: Mine Safety - GPT 摘要',
    item_5_summary TEXT NULL COMMENT 'Item 5: Market for Common Equity - GPT 摘要（含附錄支持數據）',
    item_6_summary TEXT NULL COMMENT 'Item 6: Selected Financial Data - GPT 摘要（含附錄支持數據）',
    item_7_summary TEXT NULL COMMENT 'Item 7: MD&A - GPT 摘要（含附錄支持數據）',
    item_7a_summary TEXT NULL COMMENT 'Item 7A: Market Risk - GPT 摘要（含附錄支持數據）',
    item_8_summary TEXT NULL COMMENT 'Item 8: Financial Statements - GPT 摘要（含附錄支持數據）',
    item_9_summary TEXT NULL COMMENT 'Item 9: Accountant Changes - GPT 摘要',
    item_9a_summary TEXT NULL COMMENT 'Item 9A: Controls and Procedures - GPT 摘要',
    item_9b_summary TEXT NULL COMMENT 'Item 9B: Other Information - GPT 摘要',
    item_10_summary TEXT NULL COMMENT 'Item 10: Directors and Governance - GPT 摘要（含附錄支持數據）',
    item_11_summary TEXT NULL COMMENT 'Item 11: Executive Compensation - GPT 摘要（含附錄支持數據）',
    item_12_summary TEXT NULL COMMENT 'Item 12: Security Ownership - GPT 摘要（含附錄支持數據）',
    item_13_summary TEXT NULL COMMENT 'Item 13: Related Transactions - GPT 摘要',
    item_14_summary TEXT NULL COMMENT 'Item 14: Accountant Fees - GPT 摘要（含附錄支持數據）',
    item_15_summary TEXT NULL COMMENT 'Item 15: Exhibits - GPT 摘要（含附錄支持數據）',
    item_16_summary TEXT NULL COMMENT 'Item 16: Form 10-K Summary - GPT 摘要',
    
    -- 摘要統計資訊
    items_processed_count INT DEFAULT 0 COMMENT '已完成摘要的 Item 數量',
    total_items_count INT DEFAULT 16 COMMENT '總 Item 數量',
    processing_time_seconds INT NULL COMMENT 'GPT 處理總耗時（秒）',
    
    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    
    -- 外鍵約束
    CONSTRAINT fk_ten_k_summary_original 
        FOREIGN KEY (original_filing_id) 
        REFERENCES ten_k_filings(id) 
        ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_original_filing_id (original_filing_id),
    INDEX idx_company_report_date (company_name, report_date),
    INDEX idx_processing_status (processing_status),
    INDEX idx_summary_completed_at (summary_completed_at),
    
    -- 唯一約束：確保每個原始檔案只有一個摘要版本
    UNIQUE KEY uk_one_summary_per_filing (original_filing_id)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='10-K檔案 GPT 摘要內容表';

-- ====================================================
-- 創建摘要進度視圖
-- ====================================================
CREATE OR REPLACE VIEW ten_k_summary_progress AS
SELECT 
    s.id,
    s.file_name,
    s.company_name,
    s.report_date,
    s.processing_status,
    s.items_processed_count,
    s.total_items_count,
    ROUND((s.items_processed_count / s.total_items_count) * 100, 2) as completion_percentage,
    s.processing_time_seconds,
    s.summary_completed_at,
    s.created_at
FROM ten_k_filings_summary s
ORDER BY s.report_date DESC;

-- ====================================================
-- 創建摘要內容統計視圖
-- ====================================================
CREATE OR REPLACE VIEW ten_k_summary_stats AS
SELECT 
    COUNT(*) as total_summaries,
    SUM(CASE WHEN processing_status = 'completed' THEN 1 ELSE 0 END) as completed_summaries,
    SUM(CASE WHEN processing_status = 'failed' THEN 1 ELSE 0 END) as failed_summaries,
    SUM(CASE WHEN processing_status = 'processing' THEN 1 ELSE 0 END) as processing_summaries,
    SUM(CASE WHEN processing_status = 'pending' THEN 1 ELSE 0 END) as pending_summaries,
    AVG(items_processed_count) as avg_items_per_summary,
    AVG(processing_time_seconds) as avg_processing_time_seconds,
    MIN(report_date) as earliest_report,
    MAX(report_date) as latest_report
FROM ten_k_filings_summary;

-- ====================================================
-- 插入測試資料說明（註解）
-- ====================================================
/*
-- 範例：插入測試摘要記錄
INSERT INTO ten_k_filings_summary (
    original_filing_id, 
    file_name, 
    company_name, 
    report_date,
    processing_status
) VALUES (
    1, 
    '0000320193-24-000123.txt', 
    'Apple Inc.', 
    '2024-09-28',
    'pending'
);
*/

-- ====================================================
-- 檢查創建結果
-- ====================================================
-- 顯示表結構
DESCRIBE ten_k_filings_summary;

-- 顯示視圖
SHOW CREATE VIEW ten_k_summary_progress;

-- 顯示創建成功訊息
SELECT 
    'ten_k_filings_summary 表已成功創建' as status,
    'ten_k_summary_progress 視圖已成功創建' as view_status,
    'ten_k_summary_stats 視圖已成功創建' as stats_view_status; 