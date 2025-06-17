-- 刪除舊表並重建
DROP TABLE IF EXISTS `filings`;

CREATE TABLE `filings` (
	`id` INT(11) NOT NULL AUTO_INCREMENT,
	`cik` VARCHAR(20) NOT NULL COLLATE 'utf8mb4_unicode_ci',
	`company_name` VARCHAR(200) NOT NULL COLLATE 'utf8mb4_unicode_ci',
	`filing_type` VARCHAR(20) NOT NULL COLLATE 'utf8mb4_unicode_ci',
	`filing_year` INT(4) NULL DEFAULT NULL COMMENT '財報年份',
	`accession_number` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
	`report_date` DATE NULL DEFAULT NULL,
	`filed_date` DATE NULL DEFAULT NULL,
	`file_url` VARCHAR(500) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
	`filepath` VARCHAR(500) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
	`content_summary` TEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
	`created_at` DATETIME NULL DEFAULT current_timestamp(),
	
	-- 10K財報專用欄位
	`item_1_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 1. Business',
	`item_1a_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 1A. Risk Factors',
	`item_2_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 2. Properties',
	`item_7_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 7. MD&A',
	`item_7a_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 7A. Market Risk',
	`item_8_content` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Item 8. Financial Statements',
	
	-- Form 4專用欄位
	`non_derivative_table` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Non-Derivative Securities',
	`derivative_table` LONGTEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci' COMMENT 'Derivative Securities',
	
	PRIMARY KEY (`id`) USING BTREE,
	UNIQUE INDEX `accession_number` (`accession_number`) USING BTREE,
	INDEX `idx_cik` (`cik`) USING BTREE,
	INDEX `idx_filing_type` (`filing_type`) USING BTREE,
	INDEX `idx_company_name` (`company_name`) USING BTREE,
	INDEX `idx_report_date` (`report_date`) USING BTREE,
	INDEX `idx_report_date_company` (`report_date`, `company_name`) USING BTREE,
	INDEX `idx_filing_type_date` (`filing_type`, `report_date`) USING BTREE,
	INDEX `idx_filing_year` (`filing_year`) USING BTREE
)
COMMENT='財報檔案表'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=1; 