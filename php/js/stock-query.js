// 股票查詢相關函數

// 股票查詢功能
function searchStock() {
    const ticker = document.getElementById('stock-ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        alert('請輸入股票代號');
        return;
    }

    // 顯示載入狀態
    const resultArea = document.getElementById('stock-result-area');
    resultArea.style.display = 'block';
    resultArea.innerHTML = `
        <div class="stock-loading">
            <div class="spinner-large"></div>
            <h4>正在查詢 ${ticker} 的股票資訊...</h4>
            <p>請稍候，正在檢查資料庫並獲取最新數據</p>
        </div>
    `;

    // 發送請求到後端
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
                首次分析該股票需要 2-5 分鐘，我們正在從多個數據源獲取完整的財務資訊
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
                    ${generateVerticalGrowthTable(financialData.growth_rates)}
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
                    ${generateVerticalAbsoluteMetricsTable(financialData.absolute_metrics)}
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
                    ${generateVerticalBalanceSheetTable(financialData.balance_sheet_data)}
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

        <!-- 股票問答區塊 -->
        <div class="stock-qa-section" id="qa-section-${stockInfo.symbol}">
            <div class="qa-header">
                <h4><i class="bi bi-chat-square-text"></i> 針對 ${stockInfo.symbol} 的智能問答</h4>
            </div>

            <!-- 問答歷史 -->
            <div class="qa-history" id="qa-history-${stockInfo.symbol}">
                <div class="loading-qa-history">
                    <i class="bi bi-hourglass-split"></i> 正在載入對話歷史...
                </div>
            </div>

            <!-- 問題輸入區 -->
            <div class="qa-input-area">
                <!-- 建議問題 -->
                <div class="qa-suggested-questions">
                    <button class="suggested-question-btn" onclick="askSuggestedQuestion('${stockInfo.symbol}', '公司的主要業務和產品是什麼？')">主要業務</button>
                    <button class="suggested-question-btn" onclick="askSuggestedQuestion('${stockInfo.symbol}', '最主要的風險因素有哪些？')">風險因素</button>
                    <button class="suggested-question-btn" onclick="askSuggestedQuestion('${stockInfo.symbol}', '近年來的財務表現如何？')">財務表現</button>
                    <button class="suggested-question-btn" onclick="askSuggestedQuestion('${stockInfo.symbol}', '競爭優勢和市場地位如何？')">競爭優勢</button>
                </div>
                
                <form class="qa-input-form" onsubmit="return false;">
                    <textarea 
                        id="qa-question-input-${stockInfo.symbol}" 
                        class="qa-input" 
                        placeholder="請針對 ${stockInfo.symbol} 提出您的問題..."
                        rows="2"
                    ></textarea>
                    <button 
                        type="button"
                        class="qa-submit-btn" 
                        onclick="askStockQuestion('${stockInfo.symbol}')"
                    >
                        <i class="bi bi-send"></i>
                    </button>
                </form>
            </div>
        </div>
    `;

    // 異步載入10-K檔案列表
    console.log('🚀 準備調用 getTenKFiles，股票代號:', stockInfo.symbol);
    getTenKFiles(stockInfo.symbol).then(tenKFilesHtml => {
        console.log('✅ getTenKFiles 完成，更新 HTML');
        document.getElementById('ten-k-files-section').innerHTML = tenKFilesHtml;
    }).catch(error => {
        console.error('❌ getTenKFiles 失敗:', error);
    });

    // 載入問答歷史
    loadStockQAHistory(stockInfo.symbol);
    
    // 記錄到股票查詢歷史
    addStockToHistory(stockInfo.symbol, stockInfo.company_name);
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
    
    const stockHistory = JSON.parse(localStorage.getItem('stockQueryHistory') || '[]');
    
    if (stockHistory.length === 0) {
        historyContainer.innerHTML = `
            <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                暫無股票查詢記錄<br>
                <small style="font-size: 12px;">點擊「股票查詢」開始查詢</small>
            </div>
        `;
        return;
    }
    
    historyContainer.innerHTML = `
        <div class="mb-2" style="color: #8e8ea0; font-size: 12px; padding: 0 12px;">
            最近查詢
        </div>
    ` + stockHistory.map(item => `
        <div class="history-item" data-stock-symbol="${item.ticker}">
            <div class="history-content" onclick="loadStockFromHistory('${item.ticker}')">
                <i class="bi bi-graph-up"></i>
                <div class="question-preview">
                    <div style="font-weight: 500;">${item.ticker}</div>
                    <div style="font-size: 12px; color: #8e8ea0; margin-top: 2px;">
                        ${item.companyName || '股票查詢'}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// 獲取10-K檔案列表
function getTenKFiles(ticker) {
    console.log('🔍 開始獲取10-K檔案，股票代號:', ticker);
    
    const formData = new FormData();
    formData.append('action', 'get_10k_files');
    formData.append('ticker', ticker);

    // 驗證 FormData 內容
    console.log('📤 發送10-K API請求，參數:', {action: 'get_10k_files', ticker: ticker});
    for (let [key, value] of formData.entries()) {
        console.log('📝 FormData 欄位:', key, '=', value);
    }

    return fetch('stock_api.php', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('📥 收到10-K API響應，狀態:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('🗂️ 10-K 檔案 API 回應:', data); // 調試信息
            
            // 修正邏輯：檢查是否有檔案數據，而不是只檢查 success
            if (data.files && Array.isArray(data.files) && data.files.length > 0) {
                return `
                    <div class="financial-section">
                        <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                        <div class="ten-k-files-container">
                            <div class="files-grid">
                                ${data.files.map(file => `
                                    <div class="file-item" onclick="openTenKFile('${ticker}', '${file.filename}')">
                                        <div class="file-icon">
                                            <i class="bi bi-file-earmark-text"></i>
                                        </div>
                                        <div class="file-info">
                                            <div class="file-name">${file.filename}</div>
                                            <div class="file-details">
                                                <small>檔案大小: ${file.size || 'N/A'}</small>
                                                <small>修改時間: ${file.date || 'N/A'}</small>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // 顯示詳細的錯誤信息用於調試
                const errorMessage = data.error || '目前沒有找到該股票的10-K檔案';
                const debugInfo = data.debug_info ? JSON.stringify(data.debug_info, null, 2) : '';
                
                return `
                    <div class="financial-section">
                        <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                        <div class="no-data-message">
                            <p>${errorMessage}</p>
                            <small>系統將持續更新財報檔案</small>
                            ${debugInfo ? `<details style="margin-top: 10px;"><summary>調試信息</summary><pre style="font-size: 10px; text-align: left;">${debugInfo}</pre></details>` : ''}
                        </div>
                    </div>
                `;
            }
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

// 開啟10-K檔案
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