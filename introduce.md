# FinBot 財務報表分析機器人系統詳細設計

---

## 一、系統模組概覽

FinBot 是一套精準利用 SEC EDGAR 財務報表資料的問答型分析機器人，能夠根據用戶提問，從之前問題紀錄或未分析過的新資料中尋找答案，並為用戶存成歷史記錄。

---

## 二、資料表設計

### 1. `users`

| 欄位             | 類型       | 說明      |
| -------------- | -------- | ------- |
| id             | int (PK) | 唯一用戶 ID |
| username       | varchar  | 帳號      |
| password\_hash | varchar  | 加密密碼    |
| nickname       | varchar  | 暱稱      |
| note           | text     | 備註      |
| created\_at    | datetime | 庫入時間(UTC+8)    |

### 2. `filings`

| 欄位                | 類型       | 說明                   |
| ----------------- | -------- | -------------------- |
| id                | int (PK) | 唯一 ID                |
| cik               | varchar  | 公司 CIK 編號            |
| company\_name     | varchar  | 公司名稱                 |
| filing\_type      | varchar  | 報表類型 (10-K, 10-Q...) |
| accession\_number | varchar  | SEC 編號               |
| report\_date      | date     | 報告範圍截止日              |
| filed\_date       | date     | 提交日                  |
| file\_url         | varchar  | 上傳至服務器的 URL          |
| filepath          | varchar  | 位於磁碟的相對路徑            |

### 3. `questions`

| 欄位          | 類型       | 說明              |
| ----------- | -------- | --------------- |
| id          | int (PK) |                 |
| question    | text     | 問題文字            |
| answer      | longtext | GPT 回答          |
| filing\_id  | int (FK) | 關聯 `filings.id` |
| created\_by | int (FK) | 用戶編號            |
| created\_at | datetime | 問題時間(UTC+8)            |

### 4. `user_questions`

| 欄位           | 類型       | 說明 |
| ------------ | -------- | -- |
| id           | int (PK) |    |
| user\_id     | int (FK) |    |
| question\_id | int (FK) |    |
| asked\_at    | datetime |    |

---

## 三、資料檔分析與引入

### 檔名格式

例如：

```
0000320193-17-000009.txt
```

* `0000320193` = CIK
* `17` = 提交年份
* `000009` = 當年第 9 份文件

### 前幾行可抓取信息：

```text
<ACCESSION NUMBER>:       0000320193-17-000009
<CONFORMED SUBMISSION TYPE>: 10-Q
<CONFORMED PERIOD OF REPORT>: 20170701
<FILED AS OF DATE>:       20170802
COMPANY CONFORMED NAME:   APPLE INC
CENTRAL INDEX KEY:        0000320193
```

### 簡易程式：

```python
def extract_filing_metadata(file_path):
    result = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'ACCESSION NUMBER' in line:
                result['accession_number'] = line.split(':')[-1].strip()
            elif 'CONFORMED SUBMISSION TYPE' in line:
                result['filing_type'] = line.split(':')[-1].strip()
            elif 'CONFORMED PERIOD OF REPORT' in line:
                result['report_date'] = line.split(':')[-1].strip()
            elif 'FILED AS OF DATE' in line:
                result['filed_date'] = line.split(':')[-1].strip()
            elif 'COMPANY CONFORMED NAME' in line:
                result['company_name'] = line.split(':')[-1].strip()
            elif 'CENTRAL INDEX KEY' in line:
                result['cik'] = line.split(':')[-1].strip()
            if len(result) == 6:
                break
    return result
```

---

## 四、重點區塊分析 (10-K/10-Q 完整並大)

### 方法：「區段標題分割法」

### 符合主要标題 (HTML / 文字檔)

| SEC 區塊     | 意義           |
| ---------- | ------------ |
| `Item 1.`  | 公司介紹         |
| `Item 1A.` | 風險因素         |
| `Item 7.`  | 管理團隊分析 MD\&A |
| `Item 8.`  | 財務表格 (資產負債表) |

### 採用 regex 分割方式：

```python
import re

def extract_sections(text):
    pattern = re.compile(r'(Item\s+\d+[A-Z]?\.\s+.*?)(?=Item\s+\d+[A-Z]?\.|$)', re.DOTALL | re.IGNORECASE)
    sections = pattern.findall(text)
    return sections
```

---

## 五、GPT Prompt 設計

### 系統指令 (System Prompt)

```
你是一位經驗豐富的財務分析師，請根據下列資料說明回答，不可猜測，無說有據就說。
```

### 用戶問題之 Prompt

```
請根據下列資料和用戶問題進行分析：

1. 如果既有資料不夠，請用「基於所提供資料，無法回答」
2. 請勿自行猜測或虛構
3. 回答請附上你的分析理由
4. 如果問題無提供選項，請不要說「我選擇...」

（下線資料）
【資料】:
{{report extract}}

【用戶問題】:
{{question}}
```

---

## 六、後編支援機制

### 處理流程 Summary:

1. 用戶登入
2. 提出問題
3. 搜尋 questions 表: 如果有答案 → 回答 + 記錄 user\_questions
4. 如果沒有:

   * 查 filings 表是否已有資料
   * 如果沒有資料，啟動 secedgar 下載(要啟動類似剛剛執行的apple.py只是會把公司以及年份，還有財報內容都改成動態的，不是寫死，會隨著用戶的輸入去改變) + 預號操作
   * 剖析前章與 Item 7, 8 區塊
   * 加入 prompt 擴充問題 + 給 GPT
   * 儲存 question + answer 到 `questions`
   * 記錄用戶歷史 `user_questions`

---
