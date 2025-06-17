#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新資料庫結構，添加財務指標欄位
"""

import mysql.connector

# 資料庫配置
DB_CONFIG = {
    'host': '43.207.210.147',
    'database': 'finbot_db',
    'user': 'myuser',
    'password': '123456789',
    'charset': 'utf8mb4'
}

def update_database_schema():
    """更新資料庫結構"""
    try:
        # 連接資料庫
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ 資料庫連接成功")
        
        # 檢查欄位是否已存在
        cursor.execute("DESCRIBE filings")
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # 要添加的欄位
        new_columns = [
            ("gross_margin", "DECIMAL(10,4) NULL COMMENT '毛利率(%)'"),
            ("operating_margin", "DECIMAL(10,4) NULL COMMENT '營業利益率(%)'"),
            ("net_income_margin", "DECIMAL(10,4) NULL COMMENT '淨利率(%)'"),
            ("roe", "DECIMAL(10,4) NULL COMMENT 'ROE股東權益報酬率(%)'"),
            ("roa", "DECIMAL(10,4) NULL COMMENT 'ROA資產報酬率(%)'"),
            ("asset_turnover", "DECIMAL(10,4) NULL COMMENT '資產週轉率'"),
            ("receivables_turnover", "DECIMAL(10,4) NULL COMMENT '應收帳款週轉率'"),
            ("inventory_turnover", "DECIMAL(10,4) NULL COMMENT '存貨週轉率'"),
            ("debt_to_assets_ratio", "DECIMAL(10,4) NULL COMMENT '負債比率(%)'"),
            ("current_ratio", "DECIMAL(10,4) NULL COMMENT '流動比率'"),
            ("long_term_debt", "BIGINT NULL COMMENT '長期負債(美元)'"),
            ("total_equity", "BIGINT NULL COMMENT '股東權益(美元)'"),
            ("book_value_per_share", "DECIMAL(10,4) NULL COMMENT '每股帳面價值'"),
            ("debt_to_equity_ratio", "DECIMAL(10,4) NULL COMMENT '負債權益比'"),
            ("total_revenue", "BIGINT NULL COMMENT '總營收(美元)'"),
            ("gross_profit", "BIGINT NULL COMMENT '毛利(美元)'"),
            ("operating_income", "BIGINT NULL COMMENT '營業利益(美元)'"),
            ("net_income", "BIGINT NULL COMMENT '淨利(美元)'"),
            ("total_assets", "BIGINT NULL COMMENT '總資產(美元)'"),
            ("total_liabilities", "BIGINT NULL COMMENT '總負債(美元)'"),
            ("current_assets", "BIGINT NULL COMMENT '流動資產(美元)'"),
            ("current_liabilities", "BIGINT NULL COMMENT '流動負債(美元)'"),
            ("accounts_receivable", "BIGINT NULL COMMENT '應收帳款(美元)'"),
            ("inventory", "BIGINT NULL COMMENT '存貨(美元)'"),
            ("shares_outstanding", "BIGINT NULL COMMENT '流通股數'")
        ]
        
        # 添加缺少的欄位
        added_count = 0
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE filings ADD COLUMN {column_name} {column_definition}"
                    cursor.execute(sql)
                    print(f"✅ 添加欄位: {column_name}")
                    added_count += 1
                except mysql.connector.Error as e:
                    print(f"⚠️ 添加欄位失敗 {column_name}: {e}")
            else:
                print(f"⏭️ 欄位已存在: {column_name}")
        
        # 添加索引（如果不存在）
        try:
            cursor.execute("CREATE INDEX idx_report_date_company ON filings(report_date, company_name)")
            print("✅ 添加索引: idx_report_date_company")
        except mysql.connector.Error:
            print("⏭️ 索引已存在: idx_report_date_company")
        
        try:
            cursor.execute("CREATE INDEX idx_filing_type_date ON filings(filing_type, report_date)")
            print("✅ 添加索引: idx_filing_type_date")
        except mysql.connector.Error:
            print("⏭️ 索引已存在: idx_filing_type_date")
        
        # 提交變更
        conn.commit()
        
        print(f"\n🎉 資料庫結構更新完成！共添加 {added_count} 個新欄位")
        
    except mysql.connector.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_database_schema() 