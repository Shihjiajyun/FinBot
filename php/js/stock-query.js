// 股票查詢相關函數

// 股票查詢功能
function searchStock() {
    let ticker = document.getElementById('stock-ticker-input').value.trim().toUpperCase();
    
    if (!ticker) {
        alert('請輸入股票代號');
        return;
    }

    // 基本股票代號格式驗證（支援所有股票代號）
    if (!isValidTicker(ticker)) {
        alert('請輸入有效的股票代號格式（如：AAPL, MSFT, GOOGL）');
        return;
    }

    // 更新輸入框顯示標準化後的股票代號
    document.getElementById('stock-ticker-input').value = ticker;

    // 顯示載入狀態
    const resultArea = document.getElementById('stock-result-area');
    resultArea.style.display = 'block';
    resultArea.innerHTML = `
        <div class="stock-loading">
            <div class="spinner-large"></div>
            <h4>正在查詢 ${ticker}...</h4>
            <p>請稍候，正在獲取股票資訊和財務數據</p>
        </div>
    `;

    // 發送查詢請求
    const formData = new FormData();
    formData.append('action', 'get_stock_info');
    formData.append('ticker', ticker);

    fetch('stock_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 檢查是否需要分析
            if (data.status === 'analyzing' && data.needs_analysis) {
                showAnalyzingState(ticker, data.message);
                // 啟動背景分析
                startBackgroundAnalysis(ticker);
            } else if (data.status === 'analyzing') {
                showAnalyzingState(ticker, data.message);
                // 開始輪詢檢查分析狀態
                pollAnalysisStatus(ticker);
            } else {
                displayStockInfo(data.stock_info, data.financial_data, data.data_freshly_analyzed);
            }
        } else {
            resultArea.innerHTML = `
                <div class="stock-error">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                    <h4>查詢失敗</h4>
                    <p>${data.error}</p>
                    <button onclick="searchStock()" class="retry-btn">重試</button>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('查詢錯誤:', error);
        resultArea.innerHTML = `
            <div class="stock-error">
                <i class="bi bi-wifi-off" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                <h4>網路錯誤</h4>
                <p>無法連接到伺服器，請檢查網路連線</p>
                <button onclick="searchStock()" class="retry-btn">重試</button>
            </div>
        `;
    });
}

// 驗證股票代號格式（支援所有有效的股票代號格式）
function isValidTicker(ticker) {
    // 美股代號通常是1-5個字母，可能包含點號（如 BRK.A）
    const tickerPattern = /^[A-Z]{1,5}(\.[A-Z])?$/;
    
    // 基本格式驗證
    if (!tickerPattern.test(ticker)) {
        return false;
    }
    
    // 排除一些明顯無效的格式
    const invalidPatterns = [
        /^[0-9]+$/,  // 純數字
        /^[A-Z]{6,}$/,  // 超過5個字母（不含點號）
    ];
    
    for (let pattern of invalidPatterns) {
        if (pattern.test(ticker)) {
            return false;
        }
    }
    
    return true;
}

// 顯示分析狀態
function showAnalyzingState(ticker, message) {
    const resultArea = document.getElementById('stock-result-area');
    resultArea.innerHTML = `
        <div class="stock-analyzing">
            <div class="analyzing-animation">
                <div class="spinner-large"></div>
                <div class="analyzing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            <h3>🤖 FinBot 正在分析 ${ticker}</h3>
            <p>${message}</p>
            <div class="analyzing-steps">
                <div class="step active" id="step-1">
                    <i class="bi bi-search"></i> 搜尋財務數據
                </div>
                <div class="step" id="step-2">
                    <i class="bi bi-cloud-download"></i> 下載 Macrotrends 數據
                </div>
                <div class="step" id="step-3">
                    <i class="bi bi-graph-up"></i> 獲取 Yahoo Finance 數據
                </div>
                <div class="step" id="step-4">
                    <i class="bi bi-database"></i> 存入資料庫
                </div>
            </div>
            <div class="analyzing-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <p class="progress-text">正在進行第 1 步...</p>
            </div>
            <p class="analyzing-note">
                <i class="bi bi-info-circle"></i> 
                首次分析該股票需要 2 分鐘，我們正在從多個數據源獲取完整的財務資訊
            </p>
        </div>
    `;
}

// 輪詢分析狀態
function pollAnalysisStatus(ticker) {
    let step = 1;
    let pollCount = 0;
    const maxPolls = 60; // 最多輪詢5分鐘（每5秒一次）
    
    const interval = setInterval(() => {
        pollCount++;
        
        // 更新進度條和步驟
        updateAnalysisProgress(step, pollCount);
        
        // 每15秒切換到下一步
        if (pollCount % 3 === 0) {
            step = Math.min(step + 1, 4);
        }
        
        // 檢查是否完成
        if (pollCount >= maxPolls) {
            clearInterval(interval);
            
            // 重新查詢結果
            const formData = new FormData();
            formData.append('action', 'get_stock_info');
            formData.append('ticker', ticker);
            
            fetch('stock_api.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.status !== 'analyzing') {
                    displayStockInfo(data.stock_info, data.financial_data, true);
                } else {
                    showAnalysisTimeout(ticker);
                }
            })
            .catch(error => {
                showAnalysisTimeout(ticker);
            });
        }
    }, 5000); // 每5秒檢查一次
}

// 更新分析進度
function updateAnalysisProgress(step, pollCount) {
    // 更新步驟狀態
    for (let i = 1; i <= 4; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (stepEl) {
            stepEl.classList.remove('active', 'completed');
            if (i < step) {
                stepEl.classList.add('completed');
            } else if (i === step) {
                stepEl.classList.add('active');
            }
        }
    }
    
    // 更新進度條
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    
    if (progressFill && progressText) {
        const progress = Math.min((pollCount / 60) * 100, 100);
        progressFill.style.width = `${progress}%`;
        
        const stepTexts = [
            "正在搜尋財務數據...",
            "正在下載 Macrotrends 數據...",
            "正在獲取 Yahoo Finance 數據...",
            "正在存入資料庫..."
        ];
        
        progressText.textContent = stepTexts[step - 1] || "正在完成分析...";
    }
}

// 顯示分析超時
function showAnalysisTimeout(ticker) {
    const resultArea = document.getElementById('stock-result-area');
    resultArea.innerHTML = `
        <div class="stock-error">
            <i class="bi bi-clock-history" style="font-size: 3rem; color: #ffc107; margin-bottom: 20px;"></i>
            <h4>分析超時</h4>
            <p>股票 ${ticker} 的分析可能需要更長時間，請稍後再試</p>
            <div class="timeout-actions">
                <button onclick="searchStock()" class="retry-btn">重新查詢</button>
                <button onclick="forceAnalysis('${ticker}')" class="force-btn">強制重新分析</button>
            </div>
        </div>
    `;
}

// 強制重新分析
function forceAnalysis(ticker) {
    const resultArea = document.getElementById('stock-result-area');
    resultArea.innerHTML = `
        <div class="stock-loading">
            <div class="spinner-large"></div>
            <h4>正在強制重新分析 ${ticker}...</h4>
            <p>請稍候，這可能需要幾分鐘時間</p>
        </div>
    `;
    
    const formData = new FormData();
    formData.append('action', 'analyze_financial_data');
    formData.append('ticker', ticker);
    
    fetch('stock_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            console.log('強制分析響應:', text);
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error('JSON 解析失敗:', e);
                throw new Error('伺服器返回無效的 JSON 格式');
            }
        });
    })
    .then(data => {
        if (data.success) {
            // 分析完成，重新查詢股票資訊
            searchStock();
        } else {
            resultArea.innerHTML = `
                <div class="stock-error">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                    <h4>強制分析失敗</h4>
                    <p>${data.error}</p>
                    <button onclick="searchStock()" class="retry-btn">重試</button>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('強制分析錯誤:', error);
        resultArea.innerHTML = `
            <div class="stock-error">
                <i class="bi bi-wifi-off" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                <h4>分析錯誤</h4>
                <p>錯誤詳情: ${error.message}</p>
                <button onclick="searchStock()" class="retry-btn">重試</button>
            </div>
        `;
    });
}

// 快速搜尋
function quickSearch(ticker) {
    document.getElementById('stock-ticker-input').value = ticker;
    searchStock();
}

// 顯示股票資訊
function displayStockInfo(stockInfo, financialData, freshlyAnalyzed = false) {
    const resultArea = document.getElementById('stock-result-area');

    // 添加調試日誌，檢查stockInfo數據
    console.log('📊 顯示股票資訊:', {
        symbol: stockInfo.symbol,
        market_cap: stockInfo.market_cap,
        market_cap_type: typeof stockInfo.market_cap,
        current_price: stockInfo.current_price,
        pe_ratio: stockInfo.pe_ratio,
        eps: stockInfo.eps,
        dividend_yield: stockInfo.dividend_yield
    });

    let financialTable = '';
    if (financialData && financialData.growth_rates && financialData.growth_rates.length > 0) {
        // 添加數據範圍信息
        const dataRangeInfo = financialData.total_years > 1 ?
            `<p class="data-info"><i class="bi bi-info-circle"></i> 基於 ${financialData.total_years} 年財務數據計算，公司名稱: ${financialData.company_name}</p>` :
            '';

        financialTable = `
            <div class="financial-section">
                <h5><i class="bi bi-graph-up-arrow"></i> 歷年財務增長率分析</h5>
                ${dataRangeInfo}
                <div class="financial-table-container">
                    ${generateHorizontalGrowthTable(financialData.growth_rates)}
                </div>
            </div>
        `;
    } else {
        financialTable = `
            <div class="financial-section">
                <h5><i class="bi bi-info-circle"></i> 財務增長率</h5>
                <div class="no-data-message">
                    <p>${financialData?.message || '目前沒有該股票的財務增長率數據'}</p>
                    <small>系統需要至少兩年的財務數據才能計算增長率</small>
                </div>
            </div>
        `;
    }

    let absoluteMetricsTable = '';
    if (financialData && financialData.absolute_metrics && financialData.absolute_metrics.length > 0) {
        absoluteMetricsTable = `
            <div class="financial-section">
                <h5><i class="bi bi-clipboard-data"></i> 財務絕對數值指標與比率分析</h5>
                <div class="financial-table-container">
                    ${generateHorizontalAbsoluteMetricsTable(financialData.absolute_metrics)}
                </div>
            </div>
        `;
    } else {
        absoluteMetricsTable = `
            <div class="financial-section">
                <h5><i class="bi bi-clipboard-data"></i> 財務絕對數值指標與比率分析</h5>
                <div class="no-data-message">
                    <p>目前沒有該股票的財務絕對數值數據</p>
                    <small>系統正在努力收集更多財務數據</small>
                </div>
            </div>
        `;
    }

    let balanceSheetTable = '';
    if (financialData && financialData.balance_sheet_data && financialData.balance_sheet_data.length > 0) {
        balanceSheetTable = `
            <div class="financial-section">
                <h5><i class="bi bi-clipboard-data"></i> 歷史資產負債表財務狀況（獲利能力和流動性）</h5>
                <div class="financial-table-container">
                    ${generateHorizontalBalanceSheetTable(financialData.balance_sheet_data)}
                </div>
            </div>
        `;
    } else {
        balanceSheetTable = `
            <div class="financial-section">
                <h5><i class="bi bi-clipboard-data"></i> 歷史資產負債表財務狀況（獲利能力和流動性）</h5>
                <div class="no-data-message">
                    <p>目前沒有該股票的資產負債表數據</p>
                    <small>系統正在努力收集更多財務數據</small>
                </div>
            </div>
        `;
    }

    // 添加新分析通知
    const freshAnalysisNotice = freshlyAnalyzed ? `
        <div class="fresh-analysis-notice">
            <i class="bi bi-check-circle-fill"></i>
            <span>✨ 已為您分析最新財務數據並存入資料庫</span>
        </div>
    ` : '';

    resultArea.innerHTML = `
        ${freshAnalysisNotice}
        
        <!-- 股票資訊區域 -->
        <div class="stock-info-section">
            <div class="stock-info-header">
                <h3>${stockInfo.symbol} - ${stockInfo.company_name || '公司名稱'}</h3>
                <div class="stock-price">$${stockInfo.current_price || 'N/A'}</div>
                <div class="stock-change ${stockInfo.price_change >= 0 ? 'positive' : 'negative'}">
                    ${stockInfo.price_change >= 0 ? '+' : ''}${stockInfo.price_change || 'N/A'} (${stockInfo.price_change_percent || 'N/A'}%)
                </div>
            </div>

            <div class="financial-summary">
                <div class="summary-item">
                    <div class="label">市值</div>
                    <div class="value">${formatNumber(stockInfo.market_cap)} USD</div>
                </div>
                <div class="summary-item">
                    <div class="label">本益比 (PE)</div>
                    <div class="value">${stockInfo.pe_ratio || 'N/A'}</div>
                </div>
                <div class="summary-item">
                    <div class="label">每股盈餘 (EPS)</div>
                    <div class="value">${stockInfo.eps || 'N/A'}</div>
                </div>
                <div class="summary-item">
                    <div class="label">股息殖利率</div>
                    <div class="value">${stockInfo.dividend_yield || 'N/A'}%</div>
                </div>
                <div class="summary-item">
                    <div class="label">52週高點</div>
                    <div class="value">$${stockInfo.week_52_high || 'N/A'}</div>
                </div>
                <div class="summary-item">
                    <div class="label">52週低點</div>
                    <div class="value">$${stockInfo.week_52_low || 'N/A'}</div>
                </div>
            </div>
        </div>

        <!-- 股價走勢圖區域 -->
        <div class="stock-chart-section">
            <h5><i class="bi bi-graph-up"></i> 股價走勢圖（近6個月）</h5>
            <div class="chart-container" id="stock-price-chart-container">
                <div class="chart-loading">
                    <div class="spinner-border" role="status"></div>
                    <span>正在載入股價數據...</span>
                </div>
            </div>
        </div>

        <!-- 財務分析區塊 -->
        <div class="financial-analysis-container">
            ${financialTable}
            ${absoluteMetricsTable}
            ${balanceSheetTable}

            <div id="ten-k-files-section">
                <div class="loading-placeholder">
                    <i class="bi bi-hourglass-split"></i> 正在載入10-K檔案...
                </div>
            </div>
        </div>
    `;

    // 異步載入股價數據
    loadStockPriceChart(stockInfo.symbol);

    // 異步載入10-K檔案列表
    console.log('🚀 準備調用 getTenKFiles，股票代號:', stockInfo.symbol);
    getTenKFiles(stockInfo.symbol).then(tenKFilesHtml => {
        console.log('✅ getTenKFiles 完成，更新 HTML');
        document.getElementById('ten-k-files-section').innerHTML = tenKFilesHtml;
        // 添加checkbox監聽器
        addFilingCheckboxListeners();
    }).catch(error => {
        console.error('❌ getTenKFiles 失敗:', error);
    });

    // 不再立即記錄到股票查詢歷史，等到用戶開始10-K對話時再記錄
    // addStockToHistory(stockInfo.symbol, stockInfo.company_name);
}

// 添加股票到查詢歷史
function addStockToHistory(ticker, companyName) {
    const historyContainer = document.getElementById('chat-history');
    if (!historyContainer) return;
    
    // 檢查是否已存在
    const existingItems = historyContainer.querySelectorAll('.history-item');
    let existingItem = null;
    
    existingItems.forEach(item => {
        const stockSymbol = item.dataset.stockSymbol;
        if (stockSymbol === ticker) {
            existingItem = item;
        }
    });
    
    // 如果已存在，移到頂部
    if (existingItem) {
        historyContainer.removeChild(existingItem);
    }
    
    // 創建新的歷史項目
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item active';
    historyItem.dataset.stockSymbol = ticker;
    historyItem.innerHTML = `
        <div class="history-content" onclick="loadStockFromHistory('${ticker}')">
            <i class="bi bi-graph-up"></i>
            <div class="question-preview">
                <div style="font-weight: 500;">${ticker}</div>
                <div style="font-size: 12px; color: #8e8ea0; margin-top: 2px;">
                    ${companyName || '股票查詢'}
                </div>
            </div>
        </div>
    `;
    
    // 移除其他項目的活躍狀態
    existingItems.forEach(item => {
        item.classList.remove('active');
    });
    
    // 添加到頂部
    if (historyContainer.firstChild) {
        historyContainer.insertBefore(historyItem, historyContainer.firstChild);
    } else {
        historyContainer.appendChild(historyItem);
    }
    
    // 保存到localStorage
    saveStockHistory(ticker, companyName);
}

// 從歷史記錄載入股票
function loadStockFromHistory(ticker) {
    // 設置輸入框
    const stockInput = document.getElementById('stock-ticker-input');
    if (stockInput) {
        stockInput.value = ticker;
    }
    
    // 切換到股票查詢界面
    switchToStockQuery();
    
    // 搜索股票
    searchStock();
    
    // 更新歷史項目的活躍狀態
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 標記當前選中的項目
    const currentItem = document.querySelector(`[data-stock-symbol="${ticker}"]`);
    if (currentItem) {
        currentItem.classList.add('active');
    }
}

// 保存股票歷史到localStorage
function saveStockHistory(ticker, companyName) {
    let stockHistory = JSON.parse(localStorage.getItem('stockQueryHistory') || '[]');
    
    // 移除已存在的記錄
    stockHistory = stockHistory.filter(item => item.ticker !== ticker);
    
    // 添加到開頭
    stockHistory.unshift({
        ticker: ticker,
        companyName: companyName,
        timestamp: new Date().toISOString()
    });
    
    // 限制記錄數量
    stockHistory = stockHistory.slice(0, 20);
    
    localStorage.setItem('stockQueryHistory', JSON.stringify(stockHistory));
}

// 載入股票歷史
function loadStockHistory() {
    const historyContainer = document.getElementById('chat-history');
    if (!historyContainer) return;
    
    // 載入對話歷史而不是股票查詢歷史
    loadConversationHistory();
}

// 載入對話歷史
function loadConversationHistory() {
    const historyContainer = document.getElementById('chat-history');
    if (!historyContainer) return;
    
    // 顯示載入狀態
        historyContainer.innerHTML = `
            <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            <div style="margin-top: 10px;">載入對話歷史...</div>
        </div>
    `;
    
    // 從後端獲取對話歷史
    const formData = new FormData();
    formData.append('action', 'get_conversation_history');
    
    console.log('🔍 正在載入對話歷史...');
    
    fetch('stock_qa_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('📥 對話歷史API響應狀態:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('📊 對話歷史API回應:', data);
        if (data.success && data.conversations) {
            console.log('✅ 找到', data.conversations.length, '個對話記錄');
            displayConversationHistory(data.conversations);
        } else {
            console.log('❌ 沒有對話記錄或API失敗:', data);
            historyContainer.innerHTML = `
                <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                    暫無對話記錄<br>
                    <small style="font-size: 12px;">選擇10-K檔案開始對話</small>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('載入對話歷史錯誤:', error);
        historyContainer.innerHTML = `
            <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                載入失敗<br>
                <small style="font-size: 12px;">請稍後再試</small>
            </div>
        `;
    });
}

// 顯示對話歷史
function displayConversationHistory(conversations) {
    const historyContainer = document.getElementById('chat-history');
    if (!historyContainer) return;
    
    if (conversations.length === 0) {
        historyContainer.innerHTML = `
            <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                暫無對話記錄<br>
                <small style="font-size: 12px;">選擇10-K檔案開始對話</small>
            </div>
        `;
        return;
    }
    
    historyContainer.innerHTML = `
        <div class="mb-2" style="color: #8e8ea0; font-size: 12px; padding: 0 12px;">
            最近對話
        </div>
    ` + conversations.map(conv => {
        // 解析對話標題以提取股票代號和檔案資訊
        const titleParts = conv.title.split('_');
        const ticker = titleParts[0] || 'Unknown';
        const fileInfo = titleParts.slice(1).join('_') || '對話';
        
        // 從檔案資訊中提取年份或處理特殊情況
        let displayFileInfo = fileInfo;
        if (fileInfo !== '對話') {
            // 檢查是否是檔案名稱格式
            const yearMatch = fileInfo.match(/(\d{4})/);
            if (yearMatch) {
                displayFileInfo = `${yearMatch[1]} 年`;
            } else if (fileInfo.toLowerCase().includes('all')) {
                displayFileInfo = '全部財報';
            } else if (fileInfo.includes('.txt') || fileInfo.includes('.htm')) {
                // 如果是完整檔案名，嘗試提取年份
                const filenameYear = extractYearFromFilename(fileInfo);
                displayFileInfo = filenameYear !== fileInfo ? `${filenameYear} 年` : '財報對話';
            }
        }
        
        // 格式化時間
        const timeAgo = formatTimeAgo(conv.updated_at);
        
        return `
            <div class="history-item" data-conversation-id="${conv.conversation_id}">
                <div class="history-content" onclick="openConversation('${conv.conversation_id}', '${conv.title}')">
                    <i class="bi bi-chat-dots"></i>
                    <div class="question-preview">
                        <div class="title-display" style="font-weight: 500;" id="title-display-${conv.conversation_id}">
                            ${ticker}
                        </div>
                        <div class="title-edit" style="display: none;" id="title-edit-${conv.conversation_id}">
                            <input type="text" class="title-input" value="${conv.title}" 
                                   onkeydown="handleTitleKeydown(event, '${conv.conversation_id}')"
                                   onblur="cancelTitleEdit('${conv.conversation_id}')"
                                   style="width: 100%; font-size: 12px; padding: 2px 4px; border: 1px solid #ccc; border-radius: 3px;">
                        </div>
                        <div style="font-size: 12px; color: #8e8ea0; margin-top: 2px;">
                            ${displayFileInfo}
                        </div>
                        <div style="font-size: 11px; color: #666; margin-top: 4px;">
                            ${conv.question_count} 個問題 • ${timeAgo}
                        </div>
                    </div>
                </div>
                <div class="history-actions">
                    <button class="edit-title-btn" onclick="editConversationTitle(event, '${conv.conversation_id}')" 
                            title="編輯標題" style="background: none; border: none; color: #8e8ea0; font-size: 12px; padding: 2px;">
                        <i class="bi bi-pencil"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// 編輯對話標題
function editConversationTitle(event, conversationId) {
    event.stopPropagation(); // 防止觸發對話打開
    
    const titleDisplay = document.getElementById(`title-display-${conversationId}`);
    const titleEdit = document.getElementById(`title-edit-${conversationId}`);
    const input = titleEdit.querySelector('.title-input');
    
    titleDisplay.style.display = 'none';
    titleEdit.style.display = 'block';
    input.focus();
    input.select();
}

// 處理標題編輯鍵盤事件
function handleTitleKeydown(event, conversationId) {
    if (event.key === 'Enter') {
        event.preventDefault();
        saveConversationTitle(conversationId);
    } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelTitleEdit(conversationId);
    }
}

// 取消標題編輯
function cancelTitleEdit(conversationId) {
    const titleDisplay = document.getElementById(`title-display-${conversationId}`);
    const titleEdit = document.getElementById(`title-edit-${conversationId}`);
    
    titleDisplay.style.display = 'block';
    titleEdit.style.display = 'none';
}

// 保存對話標題
function saveConversationTitle(conversationId) {
    const titleEdit = document.getElementById(`title-edit-${conversationId}`);
    const input = titleEdit.querySelector('.title-input');
    const newTitle = input.value.trim();
    
    if (!newTitle) {
        alert('標題不能為空');
        return;
    }
    
    const formData = new FormData();
    formData.append('action', 'update_conversation_title');
    formData.append('conversation_id', conversationId);
    formData.append('new_title', newTitle);
    
    fetch('stock_qa_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新顯示的標題
            const titleDisplay = document.getElementById(`title-display-${conversationId}`);
            const titleParts = newTitle.split('_');
            const ticker = titleParts[0] || 'Unknown';
            titleDisplay.textContent = ticker;
            
            // 隱藏編輯框
            cancelTitleEdit(conversationId);
            
            // 重新載入對話歷史以確保一致性
            setTimeout(() => loadConversationHistory(), 500);
        } else {
            alert('更新標題失敗: ' + (data.error || '未知錯誤'));
        }
    })
    .catch(error => {
        console.error('更新標題錯誤:', error);
        alert('更新標題時發生錯誤');
    });
}

// 格式化時間差
function formatTimeAgo(dateString) {
    const now = new Date();
    // 將資料庫時間加上8小時（台灣時區）
    const date = new Date(dateString);
    date.setHours(date.getHours() + 8);
    
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return '剛剛';
    if (diffMins < 60) return `${diffMins}分鐘前`;
    if (diffHours < 24) return `${diffHours}小時前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-TW');
}

// 打開對話
function openConversation(conversationId, title) {
    // 解析標題以獲取股票代號和檔案名
    const titleParts = title.split('_');
    const ticker = titleParts[0];
    const filename = titleParts.slice(1).join('_');
    
    // 跳轉到對話頁面
    const params = new URLSearchParams({
        ticker: ticker,
        filename: filename,
        conversation_id: conversationId
    });
    
    const url = `tenk_chat.php?${params.toString()}`;
    window.location.href = url;
}

// 從10-K檔案名稱中提取年份
function extractYearFromFilename(filename) {
    // 支持多種檔案名稱格式
    // 例如: AAPL_10-K_2023.txt, MSFT-10K-2022.pdf, TSLA_2021_10-K.txt 等
    const yearMatch = filename.match(/20\d{2}/);
    return yearMatch ? yearMatch[0] : filename;
}

// 獲取10-K檔案列表
function getTenKFiles(ticker) {
    console.log('🔍 開始獲取10-K檔案，股票代號:', ticker);
    
    // 首先檢查解析過的財報
    const parsedFormData = new FormData();
    parsedFormData.append('action', 'check_parsed_filings');
    parsedFormData.append('ticker', ticker);

    return fetch('parse_filings.php', {
            method: 'POST',
            body: parsedFormData
        })
        .then(response => response.json())
        .then(parsedData => {
            console.log('🗃️ 解析的財報檢查結果:', parsedData);
            
            // 同時檢查下載狀態
            const downloadFormData = new FormData();
            downloadFormData.append('action', 'check_download_status');
            downloadFormData.append('ticker', ticker);
            
            return fetch('download_filings.php', {
                method: 'POST',
                body: downloadFormData
            })
            .then(response => response.json())
            .then(downloadData => {
                console.log('📁 下載狀態檢查結果:', downloadData);
                
                return generateTenKFilesHTML(ticker, parsedData, downloadData);
            });
        })
        .catch(error => {
            console.error('獲取10-K檔案錯誤:', error);
            return `
                <div class="financial-section">
                    <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                    <div class="no-data-message">
                        <p>載入10-K檔案時發生錯誤</p>
                        <small>請稍後再試</small>
                    </div>
                </div>
            `;
        });
}

function generateTenKFilesHTML(ticker, parsedData, downloadData) {
    const hasParsedFiles = parsedData.success && parsedData.filings && parsedData.filings.length > 0;
    const hasDownloadedFiles = downloadData.success && downloadData.files && Object.keys(downloadData.files).length > 0;
    
    // 如果有解析過的財報，顯示財報選擇界面
    if (hasParsedFiles) {
        const allFilesCheckboxes = parsedData.filings.map(filing => {
            const summaryStatus = filing.summary_status || 'not_started';
            const summaryIcon = summaryStatus === 'completed' ? 'check-circle-fill text-success' : 
                               summaryStatus === 'processing' ? 'clock text-warning' : 
                               'circle text-muted';
            
            return `
                <div class="filing-checkbox-item">
                    <input type="checkbox" id="filing-${filing.id}" value="${filing.id}" class="filing-checkbox">
                    <label for="filing-${filing.id}" class="filing-label">
                        <div class="filing-info">
                            <span class="filing-year">${filing.year} 年</span>
                            <small class="filing-details">
                                10-K 財報 • ${filing.report_date || '日期未知'}
                            </small>
                        </div>
                        <div class="filing-status">
                            <i class="bi bi-${summaryIcon}" title="${summaryStatus === 'completed' ? '已摘要' : summaryStatus === 'processing' ? '摘要中' : '未摘要'}"></i>
                        </div>
                    </label>
                </div>
            `;
        }).join('');
        
        const html = `
            <div class="financial-section">
                <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                <div class="ten-k-files-container">
                    <div class="filing-selection-controls">
                        <div class="selection-buttons">
                            <button class="select-all-btn" onclick="selectAllFilings(true)">
                                <i class="bi bi-check-square"></i> 全選
                            </button>
                            <button class="select-none-btn" onclick="selectAllFilings(false)">
                                <i class="bi bi-square"></i> 全不選
                            </button>
                        </div>
                                            <button class="start-chat-btn" onclick="startTenKChat('${ticker}')" disabled>
                        <i class="bi bi-chat-dots-fill"></i>
                        <div class="btn-text">
                            <span class="btn-main">開始 AI 對話</span>
                            <span class="btn-sub">分析已選財報</span>
                        </div>
                    </button>
                    </div>
                    
                    <div class="filing-selection-list">
                        ${allFilesCheckboxes}
                    </div>
                    
                    <p class="filing-help-text">
                        <i class="bi bi-info-circle"></i>
                        選擇您想要分析的財報年份，然後點擊「開始對話」來與 FinBot 討論這些財報內容。
                    </p>
                </div>
            </div>
        `;
        
        // 延遲添加事件監聽器，確保DOM已渲染
        setTimeout(() => addFilingCheckboxListeners(), 100);
        
        return html;
    }
    
    // 如果有下載的檔案但未解析，顯示解析按鈕
    if (hasDownloadedFiles) {
        // 從檔案名稱中提取年份並排序
        const sortedFiles = Object.values(downloadData.files)
            .map(file => {
                // 從檔案名稱中提取年份 (例如: 0001326801-21-000014.txt -> 2021)
                const yearMatch = file.filename.match(/(\d{2})-\d{6}\.txt$/);
                if (yearMatch) {
                    const shortYear = parseInt(yearMatch[1]);
                    const fullYear = shortYear >= 90 ? 1900 + shortYear : 2000 + shortYear;
                    return { ...file, displayYear: fullYear };
                }
                // 備用邏輯：嘗試從其他位置提取年份
                const altYearMatch = file.filename.match(/(\d{4})/);
                const displayYear = altYearMatch ? parseInt(altYearMatch[1]) : '未知';
                return { ...file, displayYear: displayYear };
            })
            .sort((a, b) => b.displayYear - a.displayYear); // 按年份降序排列
        
        const filesList = sortedFiles.map(file => 
            `<li>${file.displayYear} 年</li>`
        ).join('');
        
        return `
            <div class="financial-section">
                <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                <div class="ten-k-files-container">
                    <div class="download-status">
                        <i class="bi bi-check-circle text-success"></i>
                        <span>已下載 ${Object.keys(downloadData.files).length} 份財報</span>
                    </div>
                    
                    <div class="downloaded-files-list">
                        <ul>${filesList}</ul>
                    </div>
                    
                    <div class="parse-section">
                        <p>財報已下載，需要解析後才能開始對話：</p>
                        <button class="parse-files-btn" onclick="parseDownloadedFiles('${ticker}')">
                            <i class="bi bi-gear"></i> 解析財報
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 如果沒有任何檔案，顯示下載選項
    return `
        <div class="financial-section">
            <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
            <div class="ten-k-files-container">
                <div class="no-files-message">
                    <i class="bi bi-download"></i>
                    <h6>尚未下載 ${ticker} 的 10-K 財報</h6>
                    <p>點擊下方按鈕下載最近 5 年的 10-K 財報，下載後系統會自動解析並準備對話功能。</p>
                    
                    <button class="download-files-btn" onclick="downloadTenKFiles('${ticker}')">
                        <i class="bi bi-cloud-download"></i> 下載 10-K 財報
                    </button>
                </div>
            </div>
        </div>
    `;
}

// 全選/取消選擇檔案
function selectAllFilings(selectAll) {
    const checkboxes = document.querySelectorAll('.filing-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateStartChatButton();
}

// 更新開始對話按鈕狀態
function updateStartChatButton() {
    const checkboxes = document.querySelectorAll('.filing-checkbox:checked');
    const startBtn = document.querySelector('.start-chat-btn');
    if (startBtn) {
        startBtn.disabled = checkboxes.length === 0;
    }
}

// 開始10-K對話
function startTenKChat(ticker) {
    const checkedBoxes = document.querySelectorAll('.filing-checkbox:checked');
    if (checkedBoxes.length === 0) {
        alert('請至少選擇一份財報');
        return;
    }
    
    const filingIds = Array.from(checkedBoxes).map(cb => cb.value);
    console.log('開始對話，選中的財報ID:', filingIds);
    
    // 直接跳轉到對話頁面，讓對話頁面處理摘要邏輯
    const params = new URLSearchParams({
        ticker: ticker,
        filing_ids: filingIds.join(','),
        mode: 'summary'
    });
    window.location.href = `tenk_chat.php?${params.toString()}`;
}

// 顯示摘要 loading 狀態
function showSummaryLoadingState(ticker, filingIds) {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'summary-loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="summary-loading-modal">
            <div class="summary-loading-content">
                <div class="loading-animation">
                    <div class="spinner-large"></div>
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <h3>🤖 FinBot 正在讀取財報</h3>
                <p>正在使用 GPT 分析 ${ticker} 的 ${filingIds.length} 份 10-K 財報...</p>
                <div class="loading-steps">
                    <div class="step active">
                        <i class="bi bi-file-text"></i> 準備財報數據
                    </div>
                    <div class="step">
                        <i class="bi bi-robot"></i> GPT 摘要分析
                    </div>
                    <div class="step">
                        <i class="bi bi-chat-dots"></i> 準備對話界面
                    </div>
                </div>
                <p class="loading-note">
                    <i class="bi bi-info-circle"></i> 
                    這可能需要 1-2 分鐘，請耐心等候...
                </p>
            </div>
        </div>
    `;
    document.body.appendChild(loadingOverlay);
}

// 隱藏摘要 loading 狀態
function hideSummaryLoadingState() {
    const overlay = document.getElementById('summary-loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// 下載10-K檔案
function downloadTenKFiles(ticker) {
    const downloadBtn = document.querySelector('.download-files-btn');
    if (downloadBtn) {
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 下載中...';
    }
    
    // 顯示下載進度的 SweetAlert
    Swal.fire({
        title: `正在下載 ${ticker} 的 10-K 財報`,
        html: `
            <div class="download-progress">
                <div class="spinner-border text-primary mb-3" role="status"></div>
                <p>正在從 SEC 資料庫下載最近 5 年的 10-K 財報...</p>
                <small class="text-muted">這可能需要 1-2 分鐘，請耐心等候</small>
            </div>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    const formData = new FormData();
    formData.append('action', 'download_10k_filings');
    formData.append('ticker', ticker);
    
    fetch('download_filings.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('下載完成:', data);
            
            // 從檔案名稱中提取年份信息用於顯示
            const downloadedYears = [];
            let totalFiles = 0;
            
            // 計算總檔案數和提取年份
            const filesToProcess = data.new_files || data.existing_files || {};
            console.log('📊 下載結果數據:', data);
            
            // 檢查不同的數據結構
            if (Array.isArray(filesToProcess)) {
                // 如果是數組格式
                totalFiles = filesToProcess.length;
                filesToProcess.forEach(file => {
                    const filename = typeof file === 'string' ? file : file.filename || file;
                    const yearMatch = filename.match(/(\d{2})-\d{6}\.txt$/);
                    if (yearMatch) {
                        const shortYear = parseInt(yearMatch[1]);
                        const fullYear = shortYear >= 90 ? 1900 + shortYear : 2000 + shortYear;
                        downloadedYears.push(fullYear);
                    }
                });
            } else if (typeof filesToProcess === 'object') {
                // 如果是物件格式
                const filesList = Object.values(filesToProcess);
                totalFiles = filesList.length;
                filesList.forEach(file => {
                    const filename = typeof file === 'string' ? file : file.filename || file;
                    const yearMatch = filename.match(/(\d{2})-\d{6}\.txt$/);
                    if (yearMatch) {
                        const shortYear = parseInt(yearMatch[1]);
                        const fullYear = shortYear >= 90 ? 1900 + shortYear : 2000 + shortYear;
                        downloadedYears.push(fullYear);
                    }
                });
            }
            
            // 備用計算：如果還是 0，嘗試其他欄位
            if (totalFiles === 0 && data.total_files) {
                totalFiles = data.total_files;
            }
            if (totalFiles === 0 && data.message && data.message.includes('下載')) {
                totalFiles = '多份';
            }
            
            const yearsList = downloadedYears.length > 0 ? 
                downloadedYears.sort((a, b) => b - a).join(', ') : 
                '多個年份';
            
            // 直接開始自動解析，不再顯示中間對話框
            Swal.fire({
                title: `下載完成，開始自動解析`,
                html: `
                    <div class="progress-flow">
                        <div class="step completed">
                            <i class="bi bi-check-circle-fill text-success"></i>
                            <span>下載 ${totalFiles} 份財報 ✓</span>
                        </div>
                        <div class="step active">
                            <div class="spinner-border spinner-border-sm text-success"></div>
                            <span>自動解析財報中...</span>
                        </div>
                        <div class="step">
                            <i class="bi bi-clock"></i>
                            <span>準備對話功能</span>
                        </div>
                    </div>
                    <p><strong>${ticker}</strong> 的 ${totalFiles} 份財報已下載完成</p>
                    <p>📅 年份：<strong>${yearsList}</strong></p>
                    <hr>
                    <small class="text-muted">正在自動解析這些財報以供分析...</small>
                `,
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false
            });
            
            // 自動開始解析
            parseDownloadedFiles(ticker);
        } else {
            Swal.fire({
                icon: 'error',
                title: '下載失敗',
                text: data.error || '下載過程中發生錯誤',
                confirmButtonText: '重試',
                confirmButtonColor: '#dc3545'
            });
            
            // 恢復按鈕狀態
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="bi bi-cloud-download"></i> 下載 10-K 財報';
            }
        }
    })
    .catch(error => {
        console.error('下載請求失敗:', error);
        
        Swal.fire({
            icon: 'error',
            title: '下載失敗',
            text: '網路錯誤，請檢查網路連接後重試',
            confirmButtonText: '重試',
            confirmButtonColor: '#dc3545'
        });
        
        // 恢復按鈕狀態
        if (downloadBtn) {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<i class="bi bi-cloud-download"></i> 下載 10-K 財報';
        }
    });
}

// 解析下載的檔案
function parseDownloadedFiles(ticker) {
    const parseBtn = document.querySelector('.parse-files-btn') || document.querySelector('.download-files-btn');
    if (parseBtn) {
        parseBtn.disabled = true;
        parseBtn.innerHTML = '<i class="bi bi-gear"></i> 解析中...';
    }
    
    // 如果沒有已顯示的進度對話框，才顯示新的
    if (!Swal.isVisible()) {
        Swal.fire({
            title: `正在解析 ${ticker} 的財報`,
            html: `
                <div class="parse-progress">
                    <div class="spinner-border text-success mb-3" role="status"></div>
                    <p>正在提取和解析 10-K 財報內容...</p>
                    <small class="text-muted">這個過程需要一些時間，請稍候</small>
                </div>
            `,
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    } else {
        // 更新現有的進度對話框
        Swal.update({
            title: `正在解析 ${ticker} 的財報`,
            html: `
                <div class="progress-flow">
                    <div class="step completed">
                        <i class="bi bi-check-circle-fill text-success"></i>
                        <span>下載財報 ✓</span>
                    </div>
                    <div class="step active">
                        <div class="spinner-border spinner-border-sm text-success"></div>
                        <span>解析財報中...</span>
                    </div>
                    <div class="step">
                        <i class="bi bi-clock"></i>
                        <span>準備對話功能</span>
                    </div>
                </div>
                <p>正在提取和解析 <strong>${ticker}</strong> 的 10-K 財報內容...</p>
                <small class="text-muted">智能解析每個Item內容，請稍候...</small>
            `
        });
    }
    
    const formData = new FormData();
    formData.append('action', 'parse_10k_filings');
    formData.append('ticker', ticker);
    
    fetch('parse_filings.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('解析完成:', data);
            
            // 顯示完成狀態並自動準備對話功能
            Swal.fire({
                title: `解析完成，準備對話功能`,
                html: `
                    <div class="progress-flow">
                        <div class="step completed">
                            <i class="bi bi-check-circle-fill text-success"></i>
                            <span>下載財報 ✓</span>
                        </div>
                        <div class="step completed">
                            <i class="bi bi-check-circle-fill text-success"></i>
                            <span>解析財報 ✓</span>
                        </div>
                        <div class="step active">
                            <div class="spinner-border spinner-border-sm text-primary"></div>
                            <span>載入對話界面...</span>
                        </div>
                    </div>
                    <p><strong>${ticker}</strong> 的財報已成功解析</p>
                    <p>📄 解析了 <strong>${data.parsed_files || '多份'}</strong> 份財報</p>
                    <p>📅 日期範圍：<strong>${data.date_range?.earliest || '未知'}</strong> 至 <strong>${data.date_range?.latest || '未知'}</strong></p>
                    <hr>
                    <small class="text-muted">正在載入財報列表和對話功能...</small>
                `,
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false,
                timer: 2000,
                timerProgressBar: true
            });
            
            // 延遲重新載入界面，給用戶看到完成狀態
            setTimeout(() => {
                // 重新載入10-K檔案區域
                getTenKFiles(ticker).then(html => {
                    document.getElementById('ten-k-files-section').innerHTML = html;
                    // 添加checkbox監聽器
                    addFilingCheckboxListeners();
                    
                    // 關閉進度對話框並顯示成功訊息
                    Swal.fire({
                        icon: 'success',
                        title: '🎉 一切就緒！',
                        html: `
                            <p><strong>${ticker}</strong> 的財報分析系統已準備完成</p>
                            <div class="ready-features">
                                <div class="feature-item">
                                    <i class="bi bi-check-circle text-success"></i>
                                    <span>財報已下載並解析</span>
                                </div>
                                <div class="feature-item">
                                    <i class="bi bi-check-circle text-success"></i>
                                    <span>AI 對話功能已啟用</span>
                                </div>
                                <div class="feature-item">
                                    <i class="bi bi-check-circle text-success"></i>
                                    <span>支援多年份財報分析</span>
                                </div>
                            </div>
                            <hr>
                            <p>現在您可以：</p>
                            <ol style="text-align: left; max-width: 300px; margin: 0 auto;">
                                <li>選擇想要分析的財報年份</li>
                                <li>點擊「開始 AI 對話」按鈕</li>
                                <li>與 FinBot 討論財報內容</li>
                            </ol>
                        `,
                        confirmButtonText: '開始使用',
                        confirmButtonColor: '#28a745',
                        width: '500px'
                    }).then(() => {
                        // 自動滾動到財報選擇區域
                        document.getElementById('ten-k-files-section').scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    });
                });
            }, 2000);
        } else {
            Swal.fire({
                icon: 'error',
                title: '解析失敗',
                text: data.error || '解析過程中發生錯誤',
                confirmButtonText: '重試',
                confirmButtonColor: '#dc3545'
            });
            
            // 恢復按鈕狀態
            if (parseBtn) {
                parseBtn.disabled = false;
                parseBtn.innerHTML = '<i class="bi bi-gear"></i> 解析財報';
            }
        }
    })
    .catch(error => {
        console.error('解析請求失敗:', error);
        
        Swal.fire({
            icon: 'error',
            title: '解析失敗',
            text: '網路錯誤，請檢查網路連接後重試',
            confirmButtonText: '重試',
            confirmButtonColor: '#dc3545'
        });
        
        // 恢復按鈕狀態
        if (parseBtn) {
            parseBtn.disabled = false;
            parseBtn.innerHTML = '<i class="bi bi-gear"></i> 解析財報';
        }
    });
}

// 添加檔案checkbox監聽器
function addFilingCheckboxListeners() {
    const checkboxes = document.querySelectorAll('.filing-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateStartChatButton);
    });
}

// 開啟10-K檔案聊天室（保留舊版本兼容性）
function openTenKChat(ticker, filename) {
    // 檢查是否為所有檔案模式
    const isAllFiles = filename === 'ALL';
    
    // 構建跳轉URL
    const params = new URLSearchParams({
        ticker: ticker,
        filename: filename
    });
    
    // 跳轉到10-K聊天頁面
    const url = `tenk_chat.php?${params.toString()}`;
    window.location.href = url;
}

// 創建10-K聊天窗口
function createTenKChatWindow(ticker, filename, title) {
    // 檢查是否已存在相同的聊天窗口
    const existingWindow = document.getElementById(`tenk-chat-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`);
    if (existingWindow) {
        existingWindow.style.display = 'flex';
        return;
    }

    // 創建聊天窗口容器
    const chatWindow = document.createElement('div');
    chatWindow.id = `tenk-chat-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    chatWindow.className = 'tenk-chat-window';
    
    const isAllFiles = filename === 'ALL';
    
    chatWindow.innerHTML = `
        <div class="tenk-chat-overlay" onclick="closeTenKChatWindow('${ticker}', '${filename}')"></div>
        <div class="tenk-chat-container">
            <div class="tenk-chat-header">
                <div class="tenk-chat-title">
                    <i class="bi bi-${isAllFiles ? 'collection' : 'file-earmark-text'}"></i>
                    <span>${title}</span>
                </div>
                <button class="tenk-chat-close" onclick="closeTenKChatWindow('${ticker}', '${filename}')">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
            
            <div class="tenk-chat-content">
                <div class="tenk-chat-messages" id="tenk-messages-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}">
                    <div class="welcome-message">
                        <div class="bot-avatar">
                            <i class="bi bi-robot"></i>
                        </div>
                        <div class="message-content">
                            <h5>歡迎使用 FinBot 10-K 分析</h5>
                            <p>我可以幫您分析 ${ticker} 的${isAllFiles ? '所有' : '指定'} 10-K 財報檔案。請提出您的問題：</p>
                            <div class="suggested-questions">
                                <button class="suggested-btn" onclick="askTenKQuestion('${ticker}', '${filename}', '公司的主要業務和產品線有哪些？')">
                                    主要業務
                                </button>
                                <button class="suggested-btn" onclick="askTenKQuestion('${ticker}', '${filename}', '最主要的風險因素是什麼？')">
                                    風險因素
                                </button>
                                <button class="suggested-btn" onclick="askTenKQuestion('${ticker}', '${filename}', '財務表現和關鍵指標如何？')">
                                    財務表現
                                </button>
                                <button class="suggested-btn" onclick="askTenKQuestion('${ticker}', '${filename}', '未來的發展策略和計劃是什麼？')">
                                    未來計劃
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="tenk-chat-input">
                <div class="input-container">
                    <textarea 
                        id="tenk-input-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}"
                        placeholder="請針對${isAllFiles ? '所有' : '此份'} 10-K 檔案提出您的問題..."
                        rows="2"
                    ></textarea>
                    <button 
                        id="tenk-send-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}"
                        onclick="sendTenKQuestion('${ticker}', '${filename}')"
                    >
                        <i class="bi bi-send"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到body
    document.body.appendChild(chatWindow);
    
    // 添加Enter鍵支持
    const inputElement = document.getElementById(`tenk-input-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`);
    if (inputElement) {
        inputElement.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendTenKQuestion(ticker, filename);
            }
        });
        // 自動聚焦
        setTimeout(() => inputElement.focus(), 100);
    }
}

// 關閉10-K聊天窗口
function closeTenKChatWindow(ticker, filename) {
    const windowId = `tenk-chat-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const chatWindow = document.getElementById(windowId);
    if (chatWindow) {
        chatWindow.style.display = 'none';
    }
}

// 發送10-K問題
function sendTenKQuestion(ticker, filename) {
    const inputId = `tenk-input-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const sendBtnId = `tenk-send-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const messagesId = `tenk-messages-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    
    const inputElement = document.getElementById(inputId);
    const sendButton = document.getElementById(sendBtnId);
    const messagesContainer = document.getElementById(messagesId);
    
    if (!inputElement || !sendButton || !messagesContainer) {
        console.error('找不到聊天元素');
        return;
    }

    const question = inputElement.value.trim();
    if (!question) {
        alert('請輸入問題');
        return;
    }

    // 禁用輸入
    inputElement.disabled = true;
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';

    // 添加用戶問題
    addTenKMessage(messagesContainer, question, 'user');

    // 清空輸入框
    inputElement.value = '';

    // 顯示機器人思考狀態
    addTenKMessage(messagesContainer, '', 'bot', true);

    // 發送請求
    const formData = new FormData();
    formData.append('action', 'ask_10k_question');
    formData.append('ticker', ticker);
    formData.append('filename', filename);
    formData.append('question', question);

    fetch('stock_qa_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 移除思考狀態
        const thinkingMessage = messagesContainer.querySelector('.thinking-message');
        if (thinkingMessage) {
            thinkingMessage.remove();
        }

        if (data.success) {
            // 添加回答
            addTenKMessage(messagesContainer, data.answer, 'bot');
        } else {
            // 添加錯誤消息
            addTenKMessage(messagesContainer, `抱歉，處理您的問題時發生錯誤：${data.error}`, 'bot', false, true);
        }
    })
    .catch(error => {
        console.error('發送10-K問題失敗:', error);
        
        // 移除思考狀態
        const thinkingMessage = messagesContainer.querySelector('.thinking-message');
        if (thinkingMessage) {
            thinkingMessage.remove();
        }
        
        addTenKMessage(messagesContainer, '網路錯誤，請稍後再試', 'bot', false, true);
    })
    .finally(() => {
        // 恢復輸入狀態
        inputElement.disabled = false;
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="bi bi-send"></i>';
        inputElement.focus();
    });
}

// 添加10-K聊天消息
function addTenKMessage(messagesContainer, content, sender, isThinking = false, isError = false) {
    const messageDiv = document.createElement('div');
    
    if (isThinking) {
        messageDiv.className = 'chat-message bot thinking-message';
        messageDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="message-content">
                <div class="thinking-animation">
                    <span></span><span></span><span></span>
                </div>
                <small>FinBot 正在分析 10-K 檔案...</small>
            </div>
        `;
    } else {
        messageDiv.className = `chat-message ${sender}${isError ? ' error' : ''}`;
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="message-content">
                    ${escapeHtml(content)}
                </div>
                <div class="user-avatar">
                    <i class="bi bi-person"></i>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    ${isError ? escapeHtml(content) : formatAnswer(content)}
                </div>
            `;
        }
    }
    
    messagesContainer.appendChild(messageDiv);
    messageDiv.scrollIntoView({ behavior: 'smooth' });
}

// 提出建議的10-K問題
function askTenKQuestion(ticker, filename, question) {
    const inputId = `tenk-input-${ticker}-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const inputElement = document.getElementById(inputId);
    
    if (inputElement) {
        inputElement.value = question;
        sendTenKQuestion(ticker, filename);
    }
}

// 保留原來的 openTenKFile 函數作為備用（用於查看檔案內容）
function openTenKFile(ticker, filename) {
    // 新視窗開啟檔案檢視器
    const url = `view_10k.php?ticker=${encodeURIComponent(ticker)}&file=${encodeURIComponent(filename)}`;
    window.open(url, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
}

// 切換到股票查詢界面
function switchToStockQuery() {
    // 顯示股票查詢界面（移除聊天相關元素引用）
    document.getElementById('stock-query-container').style.display = 'block';

    // 移除歷史記錄的活躍狀態
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });

    // 清空當前對話ID，確保新的股票查詢不會影響對話歷史
    if (typeof currentConversationId !== 'undefined') {
        currentConversationId = null;
    }
}

// 為股票查詢輸入框添加Enter鍵支持
document.addEventListener('DOMContentLoaded', function() {
    const stockInput = document.getElementById('stock-ticker-input');
    if (stockInput) {
        stockInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchStock();
            }
        });
    }
    
    // 為問答輸入框添加事件監聽器 (使用事件委託)
    document.addEventListener('keydown', function(e) {
        if (e.target.matches('[id^="qa-question-input-"]') && e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const tickerMatch = e.target.id.match(/qa-question-input-(.+)/);
            if (tickerMatch) {
                askStockQuestion(tickerMatch[1]);
            }
        }
    });
});

// 啟動背景分析
function startBackgroundAnalysis(ticker) {
    // 顯示動態進度
    simulateAnalysisProgress();
    
    // 調用分析API
    const formData = new FormData();
    formData.append('action', 'analyze_financial_data');
    formData.append('ticker', ticker);
    
    fetch('stock_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            console.log('背景分析響應:', text);
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error('JSON 解析失敗:', e);
                console.error('響應內容:', text);
                throw new Error('伺服器返回無效的 JSON 格式');
            }
        });
    })
    .then(data => {
        if (data.success) {
            // 分析完成，獲取完整的股票信息並顯示
            console.log('分析完成，獲取完整股票信息...');
            setTimeout(() => {
                // 調用 get_stock_info API 獲取完整的股票信息
                const formData = new FormData();
                formData.append('action', 'get_stock_info');
                formData.append('ticker', ticker);
                
                fetch('stock_api.php', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(stockData => {
                    console.log('獲取股票信息結果:', stockData);
                    
                    if (stockData.success && stockData.stock_info) {
                        // 使用真實的股票信息和分析得到的財務數據
                        const finalFinancialData = stockData.financial_data || data.financial_data;
                        console.log('顯示完整股票信息和財務數據');
                        displayStockInfo(stockData.stock_info, finalFinancialData, true);
                    } else {
                        // 如果無法獲取股票基本信息，使用最小信息集
                        const basicStockInfo = {
                            symbol: ticker,
                            company_name: data.financial_data?.company_name || ticker,
                            exchange: 'NASDAQ/NYSE',
                            current_price: 'N/A',
                            price_change: 0,
                            price_change_percent: 'N/A',
                            market_cap: 'N/A',
                            pe_ratio: 'N/A',
                            eps: 'N/A',
                            dividend_yield: 'N/A',
                            week_52_high: 'N/A',
                            week_52_low: 'N/A',
                            avg_volume: 'N/A',
                            profit_margin: 'N/A',
                            return_on_assets: 'N/A'
                        };
                        displayStockInfo(basicStockInfo, data.financial_data, true);
                    }
                })
                .catch(error => {
                    console.error('獲取股票信息錯誤:', error);
                    // 回退到基本顯示
                    const basicStockInfo = {
                        symbol: ticker,
                        company_name: data.financial_data?.company_name || ticker,
                        exchange: 'NASDAQ/NYSE',
                        current_price: '載入中...',
                        price_change: 0,
                        price_change_percent: '載入中...',
                        market_cap: '載入中...',
                        pe_ratio: '載入中...',
                        eps: '載入中...',
                        dividend_yield: '載入中...',
                        week_52_high: '載入中...',
                        week_52_low: '載入中...',
                        avg_volume: '載入中...',
                        profit_margin: '載入中...',
                        return_on_assets: '載入中...'
                    };
                    displayStockInfo(basicStockInfo, data.financial_data, true);
                });
            }, 1000);
        } else {
            const resultArea = document.getElementById('stock-result-area');
            resultArea.innerHTML = `
                <div class="stock-error">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                    <h4>分析失敗</h4>
                    <p>${data.error}</p>
                    <button onclick="searchStock()" class="retry-btn">重試</button>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('分析錯誤:', error);
        const resultArea = document.getElementById('stock-result-area');
        resultArea.innerHTML = `
            <div class="stock-error">
                <i class="bi bi-wifi-off" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                <h4>網路錯誤</h4>
                <p>無法連接到伺服器，請檢查網路連線</p>
                <button onclick="searchStock()" class="retry-btn">重試</button>
            </div>
        `;
    });
}

// 模擬分析進度
function simulateAnalysisProgress() {
    let currentStep = 1;
    
    const stepInterval = setInterval(() => {
        updateAnalysisProgress(currentStep, 0);
        
        // 每步停留一段時間
        setTimeout(() => {
            // 標記當前步驟為完成
            const stepEl = document.getElementById(`step-${currentStep}`);
            if (stepEl) {
                stepEl.classList.remove('active');
                stepEl.classList.add('completed');
            }
            
            currentStep++;
            
            if (currentStep > 4) {
                clearInterval(stepInterval);
                // 顯示完成狀態
                const progressText = document.querySelector('.progress-text');
                if (progressText) {
                    progressText.textContent = "分析完成，正在載入結果...";
                }
                
                const progressFill = document.querySelector('.progress-fill');
                if (progressFill) {
                    progressFill.style.width = '100%';
                }
            } else {
                // 激活下一步
                const nextStepEl = document.getElementById(`step-${currentStep}`);
                if (nextStepEl) {
                    nextStepEl.classList.add('active');
                }
            }
        }, 3000); // 每步持續3秒
        
    }, 100); // 立即開始第一步
}

// === 股票問答功能 ===

// 載入股票問答歷史
function loadStockQAHistory(ticker) {
    console.log('🔄 載入股票問答歷史:', ticker);
    
    const historyContainer = document.getElementById(`qa-history-${ticker}`);
    if (!historyContainer) {
        console.error('找不到歷史容器:', `qa-history-${ticker}`);
        return;
    }

    const formData = new FormData();
    formData.append('action', 'get_stock_qa_history');
    formData.append('ticker', ticker);

    fetch('stock_qa_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayQAHistory(ticker, data.qa_history);
        } else {
            historyContainer.innerHTML = `
                <div class="no-qa-history">
                    <i class="bi bi-chat-left-text" style="font-size: 2rem; color: #8e8ea0; margin-bottom: 10px;"></i>
                    <p>還沒有關於 ${ticker} 的問答記錄</p>
                    <small>開始提問來建立對話歷史！</small>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('載入問答歷史失敗:', error);
        historyContainer.innerHTML = `
            <div class="qa-error">
                <i class="bi bi-exclamation-triangle"></i>
                <p>載入對話歷史失敗</p>
            </div>
        `;
    });
}

// 顯示問答歷史
function displayQAHistory(ticker, qaHistory) {
    const historyContainer = document.getElementById(`qa-history-${ticker}`);
    if (!historyContainer) return;

    if (!qaHistory || qaHistory.length === 0) {
        historyContainer.innerHTML = `
            <div class="no-qa-history">
                <i class="bi bi-chat-left-text" style="font-size: 2rem; color: #8e8ea0; margin-bottom: 10px;"></i>
                <p>還沒有關於 ${ticker} 的問答記錄</p>
                <small>開始提問來建立對話歷史！</small>
            </div>
        `;
        return;
    }

    let historyHtml = `
        <div class="qa-history-header">
            <h6><i class="bi bi-clock-history"></i> 對話歷史 (${qaHistory.length} 個問答)</h6>
        </div>
    `;

    qaHistory.forEach((qa, index) => {
        historyHtml += `
            <div class="qa-item" data-qa-id="${qa.id}">
                <div class="qa-question">
                    <div class="qa-content-wrapper">
                        <div class="qa-avatar">
                            <i class="bi bi-person"></i>
                        </div>
                        <div class="qa-bubble">
                            <div class="qa-meta">
                                <span class="qa-time">${formatQATime(qa.created_at)}</span>
                            </div>
                            ${escapeHtml(qa.question)}
                        </div>
                    </div>
                </div>
                <div class="qa-answer">
                    <div class="qa-content-wrapper">
                        <div class="qa-avatar">
                            <i class="bi bi-robot"></i>
                        </div>
                        <div class="qa-bubble">
                            <div class="qa-meta">
                                <span class="qa-label">FinBot 回答</span>
                                ${qa.is_cached ? '<span class="cached-badge">快取回答</span>' : ''}
                                <span class="qa-time">${formatQATime(qa.created_at)}</span>
                            </div>
                            ${formatAnswer(qa.answer)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    historyContainer.innerHTML = historyHtml;
}

// 提出股票問題
function askStockQuestion(ticker) {
    const inputElement = document.getElementById(`qa-question-input-${ticker}`);
    const sendButton = document.getElementById(`qa-send-btn-${ticker}`);
    
    if (!inputElement || !sendButton) {
        console.error('找不到輸入元素');
        return;
    }

    const question = inputElement.value.trim();
    if (!question) {
        alert('請輸入問題');
        return;
    }

    // 開始處理狀態
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';
    inputElement.disabled = true;

    // 在歷史區域添加問題
    addQuestionToHistory(ticker, question);

    const formData = new FormData();
    formData.append('action', 'ask_stock_question');
    formData.append('ticker', ticker);
    formData.append('question', question);

    fetch('stock_qa_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 添加回答到歷史
            addAnswerToHistory(ticker, data.answer, data.is_cached, data.question_id);
            
            // 清空輸入框
            inputElement.value = '';
        } else {
            // 顯示錯誤
            addErrorToHistory(ticker, data.error);
        }
    })
    .catch(error => {
        console.error('提問失敗:', error);
        addErrorToHistory(ticker, '網路錯誤，請稍後再試');
    })
    .finally(() => {
        // 恢復輸入狀態
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="bi bi-send"></i>';
        inputElement.disabled = false;
        inputElement.focus();
    });
}

// 提出建議問題
function askSuggestedQuestion(ticker, question) {
    const inputElement = document.getElementById(`qa-question-input-${ticker}`);
    if (inputElement) {
        inputElement.value = question;
        askStockQuestion(ticker);
    }
}

// 添加問題到歷史 - 使用新的左右對話佈局
function addQuestionToHistory(ticker, question) {
    const historyContainer = document.getElementById(`qa-history-${ticker}`);
    if (!historyContainer) return;

    // 如果是空歷史，先清空
    const noHistory = historyContainer.querySelector('.no-qa-history');
    if (noHistory) {
        historyContainer.innerHTML = `
            <div class="qa-history-header">
                <h6><i class="bi bi-clock-history"></i> 對話歷史</h6>
            </div>
        `;
    }

    const qaItem = document.createElement('div');
    qaItem.className = 'qa-item processing';
    qaItem.innerHTML = `
        <div class="qa-question">
            <div class="qa-content-wrapper">
                <div class="qa-avatar">
                    <i class="bi bi-person"></i>
                </div>
                <div class="qa-bubble">
                    <div class="qa-meta">
                        <span class="qa-time">剛剛</span>
                    </div>
                    ${escapeHtml(question)}
                </div>
            </div>
        </div>
        <div class="qa-answer">
            <div class="qa-content-wrapper">
                <div class="qa-avatar">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="qa-bubble">
                    <div class="qa-meta">
                        <span class="qa-label">FinBot 正在分析中...</span>
                    </div>
                    <div class="thinking-animation">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        </div>
    `;

    historyContainer.appendChild(qaItem);
    qaItem.scrollIntoView({ behavior: 'smooth' });
}

// 添加回答到歷史 - 使用新的左右對話佈局
function addAnswerToHistory(ticker, answer, isCached, questionId) {
    const historyContainer = document.getElementById(`qa-history-${ticker}`);
    if (!historyContainer) return;

    const processingItem = historyContainer.querySelector('.qa-item.processing');
    if (processingItem) {
        processingItem.classList.remove('processing');
        
        const answerBubble = processingItem.querySelector('.qa-answer .qa-bubble');
        answerBubble.innerHTML = `
            <div class="qa-meta">
                <span class="qa-label">FinBot 回答</span>
                ${isCached ? '<span class="cached-badge">快取回答</span>' : ''}
                <span class="qa-time">剛剛</span>
            </div>
            ${formatAnswer(answer)}
        `;
        
        answerBubble.scrollIntoView({ behavior: 'smooth' });
    }
}

// 添加錯誤到歷史 - 使用新的左右對話佈局
function addErrorToHistory(ticker, error) {
    const historyContainer = document.getElementById(`qa-history-${ticker}`);
    if (!historyContainer) return;

    const processingItem = historyContainer.querySelector('.qa-item.processing');
    if (processingItem) {
        processingItem.classList.remove('processing');
        processingItem.classList.add('error');
        
        const answerBubble = processingItem.querySelector('.qa-answer .qa-bubble');
        answerBubble.innerHTML = `
            <div class="qa-meta">
                <span class="qa-label">錯誤</span>
            </div>
            <div class="qa-content error-message">${escapeHtml(error)}</div>
        `;
    }
}

// 輔助函數
function formatQATime(timestamp) {
    const date = new Date(timestamp);
    // 修正時區問題 - 加8小時
    date.setHours(date.getHours() + 8);
    
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffMinutes < 1) return '剛剛';
    if (diffMinutes < 60) return `${diffMinutes} 分鐘前`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)} 小時前`;
    return date.toLocaleDateString('zh-TW');
}

function formatAnswer(answer) {
    // 檢查是否包含圖表數據
    const chartRegex = /```chart\s*([\s\S]*?)\s*```/g;
    const charts = [];
    let match;
    
    // 提取所有圖表數據
    while ((match = chartRegex.exec(answer)) !== null) {
        try {
            const chartData = JSON.parse(match[1]);
            charts.push(chartData);
        } catch (e) {
            console.error('圖表數據解析錯誤:', e);
        }
    }
    
    // 移除圖表數據標記，保留純文字內容
    let cleanAnswer = answer.replace(chartRegex, '');
    
    // 初始化並使用markdown-it渲染Markdown內容
    if (typeof markdownit !== 'undefined') {
        // 創建新的markdown-it實例
        const md = markdownit({
            html: true,
            linkify: true,
            typographer: true,
            breaks: true
        });
        
        cleanAnswer = md.render(cleanAnswer);
    } else if (typeof window.md !== 'undefined') {
        // 使用已存在的實例
        cleanAnswer = window.md.render(cleanAnswer);
    } else {
        // 如果沒有markdown-it，手動處理基本Markdown
        cleanAnswer = escapeHtml(cleanAnswer)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/^#{6}\s(.+)$/gm, '<h6>$1</h6>')
            .replace(/^#{5}\s(.+)$/gm, '<h5>$1</h5>')
            .replace(/^#{4}\s(.+)$/gm, '<h4>$1</h4>')
            .replace(/^#{3}\s(.+)$/gm, '<h3>$1</h3>')
            .replace(/^#{2}\s(.+)$/gm, '<h2>$1</h2>')
            .replace(/^#{1}\s(.+)$/gm, '<h1>$1</h1>')
            .replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>')
            .replace(/^-\s(.+)$/gm, '<li>$1</li>')
            .replace(/\n/g, '<br>');
        
        // 包裝列表項目
        cleanAnswer = cleanAnswer.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    }
    
    // 添加圖表容器
    if (charts.length > 0) {
        charts.forEach((chartData, index) => {
            const chartId = `chart-${Date.now()}-${index}`;
            cleanAnswer += `<div class="chart-container" style="margin: 20px 0; background: #1e1e1e; border-radius: 8px; padding: 15px;">
                <canvas id="${chartId}" width="400" height="200"></canvas>
            </div>`;
            
            // 延遲渲染圖表，確保DOM已更新
            setTimeout(() => {
                renderChart(chartId, chartData);
            }, 100);
        });
    }
    
    return cleanAnswer;
}

function renderChart(canvasId, chartData) {
    // 檢查是否有Chart.js庫
    if (typeof Chart === 'undefined') {
        console.error('Chart.js 庫未載入');
        return;
    }
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('找不到圖表容器:', canvasId);
        return;
    }
    
    try {
        new Chart(canvas, {
            type: chartData.type || 'line',
            data: chartData.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: !!chartData.title,
                        text: chartData.title || '',
                        color: '#ffffff'
                    },
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                ...chartData.options
            }
        });
    } catch (error) {
        console.error('圖表渲染錯誤:', error);
        canvas.parentElement.innerHTML = `<p style="color: #dc3545; text-align: center;">圖表載入失敗</p>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 快速跳轉到問答輸入區域
function scrollToStockQAInput(ticker) {
    const qaSection = document.getElementById(`qa-section-${ticker}`);
    const inputElement = document.getElementById(`qa-question-input-${ticker}`);
    
    if (qaSection) {
        qaSection.scrollIntoView({ behavior: 'smooth', block: 'end' });
        
        // 聚焦到輸入框
        setTimeout(() => {
            if (inputElement) {
                inputElement.focus();
            }
        }, 500);
    }
}

// 監控股票結果區域滾動，控制快速跳轉按鈕顯示
function initStockScrollMonitoring() {
    const stockResultArea = document.getElementById('stock-result-area');
    const quickJumpBtn = document.getElementById('stock-quick-jump-btn');
    
    if (stockResultArea && quickJumpBtn) {
        stockResultArea.addEventListener('scroll', function() {
            const scrollTop = this.scrollTop;
            const scrollHeight = this.scrollHeight;
            const clientHeight = this.clientHeight;
            
            // 檢查是否有問答區域存在，且滾動距離超過視窗高度一半
            const qaSection = document.querySelector('.stock-qa-section');
            if (qaSection && scrollTop > clientHeight / 2) {
                quickJumpBtn.classList.add('show');
            } else {
                quickJumpBtn.classList.remove('show');
            }
        });
    }
}

// 全局快速跳轉函數
function scrollToCurrentStockQA() {
    // 找到當前顯示的股票問答區域
    const qaSection = document.querySelector('.stock-qa-section');
    const stockResultArea = document.getElementById('stock-result-area');
    
    if (qaSection && stockResultArea) {
        // 滾動到問答區域
        qaSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // 聚焦到輸入框
        setTimeout(() => {
            const inputElement = qaSection.querySelector('textarea');
            if (inputElement) {
                inputElement.focus();
            }
        }, 500);
    }
}

// 在頁面載入時初始化滾動監控
document.addEventListener('DOMContentLoaded', function() {
    initStockScrollMonitoring();
});

// 載入股價走勢圖
function loadStockPriceChart(ticker) {
    const chartContainer = document.getElementById('stock-price-chart-container');
    if (!chartContainer) return;

    // 發送請求獲取股價數據
    const formData = new FormData();
    formData.append('action', 'get_stock_price_data');
    formData.append('ticker', ticker);
    formData.append('period', '6mo'); // 近6個月

    fetch('stock_api.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.price_data) {
            renderStockPriceChart(data.price_data, ticker);
        } else {
            showChartError(data.error || '無法載入股價數據');
        }
    })
    .catch(error => {
        console.error('載入股價數據失敗:', error);
        showChartError('網路錯誤，無法載入股價數據');
    });
}

// 渲染股價走勢圖
function renderStockPriceChart(priceData, ticker) {
    const chartContainer = document.getElementById('stock-price-chart-container');
    if (!chartContainer) return;

    // 創建canvas元素
    chartContainer.innerHTML = `
        <canvas id="stock-price-chart" style="max-height: 400px;"></canvas>
    `;

    const canvas = document.getElementById('stock-price-chart');
    if (!canvas) return;

    try {
        // 準備圖表數據
        const labels = priceData.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' });
        });

        const prices = priceData.map(item => parseFloat(item.close));
        const volumes = priceData.map(item => parseInt(item.volume));

        // 計算移動平均線（20日）
        const movingAverage = calculateMovingAverage(prices, 20);

        const chartData = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `${ticker} 收盤價`,
                        data: prices,
                        borderColor: '#2c5aa0',
                        backgroundColor: 'rgba(44, 90, 160, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.2,
                        pointRadius: 0,
                        pointHoverRadius: 5
                    },
                    {
                        label: '20日移動平均',
                        data: movingAverage,
                        borderColor: '#ff6b6b',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${ticker} 股價走勢（近6個月）`,
                        color: '#ffffff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        callbacks: {
                            label: function(context) {
                                if (context.datasetIndex === 0) {
                                    return `收盤價: $${context.parsed.y.toFixed(2)}`;
                                } else {
                                    return `20日均線: $${context.parsed.y.toFixed(2)}`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '日期',
                            color: '#ffffff'
                        },
                        ticks: {
                            color: '#ffffff',
                            maxTicksLimit: 10
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '價格 (USD)',
                            color: '#ffffff'
                        },
                        ticks: {
                            color: '#ffffff',
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        };

        new Chart(canvas, chartData);
        console.log('股價圖表渲染成功');

    } catch (error) {
        console.error('股價圖表渲染錯誤:', error);
        showChartError('圖表渲染失敗');
    }
}

// 計算移動平均線
function calculateMovingAverage(prices, period) {
    const movingAverage = [];
    
    for (let i = 0; i < prices.length; i++) {
        if (i < period - 1) {
            movingAverage.push(null);
        } else {
            const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
            movingAverage.push(sum / period);
        }
    }
    
    return movingAverage;
}

// 顯示圖表錯誤
function showChartError(errorMessage) {
    const chartContainer = document.getElementById('stock-price-chart-container');
    if (chartContainer) {
        chartContainer.innerHTML = `
            <div class="chart-error">
                <i class="bi bi-exclamation-triangle" style="font-size: 2rem; color: #dc3545; margin-bottom: 10px;"></i>
                <p>${errorMessage}</p>
                <small>請稍後再試或檢查網路連線</small>
            </div>
        `;
    }
}

// 修復股票數據功能
function fixStockData(ticker) {
    if (!ticker) {
        alert('請提供有效的股票代號');
        return;
    }
    
    // 顯示修復中狀態
    const fixButton = document.querySelector('.fix-data-btn');
    if (fixButton) {
        fixButton.innerHTML = '<i class="bi bi-hourglass-split"></i> 修復中...';
        fixButton.disabled = true;
    }
    
    // 調用修復API
    fetch('php/fix_stock_data.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            ticker: ticker
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 修復成功，顯示結果
            alert(`${ticker} 數據修復完成！\n數據完整度: ${data.data_completeness}%\n處理年份: ${data.years_processed} 年`);
            
            // 重新載入股票數據
            setTimeout(() => {
                searchStock();
            }, 1000);
        } else {
            // 修復失敗
            alert(`修復失敗: ${data.error || '未知錯誤'}`);
            
            // 恢復按鈕狀態
            if (fixButton) {
                fixButton.innerHTML = '修復數據';
                fixButton.disabled = false;
            }
        }
    })
    .catch(error => {
        console.error('修復數據時發生錯誤:', error);
        alert('修復數據時發生錯誤，請稍後再試');
        
        // 恢復按鈕狀態
        if (fixButton) {
            fixButton.innerHTML = '修復數據';
            fixButton.disabled = false;
        }
    });
} 