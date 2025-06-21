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
        <div class="stock-info-card">
            <div class="stock-header">
                <div class="stock-title">
                    <h3>${stockInfo.symbol}</h3>
                    <h4>${stockInfo.company_name || '公司名稱'}</h4>
                    <span class="exchange-badge">${stockInfo.exchange || 'N/A'}</span>
                </div>
                <div class="stock-price">
                    <div class="current-price">$${stockInfo.current_price || 'N/A'}</div>
                    <div class="price-change ${stockInfo.price_change >= 0 ? 'positive' : 'negative'}">
                        ${stockInfo.price_change >= 0 ? '+' : ''}${stockInfo.price_change || 'N/A'} (${stockInfo.price_change_percent || 'N/A'}%)
                    </div>
                </div>
            </div>

            <div class="stock-metrics">
                <div class="metric-row">
                    <div class="metric-item">
                        <label>市值</label>
                        <value>${formatNumber(stockInfo.market_cap)} USD</value>
                    </div>
                    <div class="metric-item">
                        <label>本益比 (PE)</label>
                        <value>${stockInfo.pe_ratio || 'N/A'}</value>
                    </div>
                    <div class="metric-item">
                        <label>每股盈餘 (EPS)</label>
                        <value>${stockInfo.eps || 'N/A'}</value>
                    </div>
                </div>
                
                <div class="metric-row">
                    <div class="metric-item">
                        <label>股息殖利率</label>
                        <value>${stockInfo.dividend_yield || 'N/A'}%</value>
                    </div>
                    <div class="metric-item">
                        <label>52週高點</label>
                        <value>$${stockInfo.week_52_high || 'N/A'}</value>
                    </div>
                    <div class="metric-item">
                        <label>52週低點</label>
                        <value>$${stockInfo.week_52_low || 'N/A'}</value>
                    </div>
                </div>
                
                <div class="metric-row">
                    <div class="metric-item">
                        <label>平均成交量</label>
                        <value>${formatNumber(stockInfo.avg_volume)}</value>
                    </div>
                    <div class="metric-item">
                        <label>淨利率</label>
                        <value>${stockInfo.profit_margin || 'N/A'}%</value>
                    </div>
                    <div class="metric-item">
                        <label>總資產收益率</label>
                        <value>${stockInfo.return_on_assets || 'N/A'}%</value>
                    </div>
                </div>
            </div>

            ${financialTable}
            ${absoluteMetricsTable}
            ${balanceSheetTable}

            <div id="ten-k-files-section">
                <div class="loading-placeholder">
                    <i class="bi bi-hourglass-split"></i> 正在載入10-K檔案...
                </div>
            </div>

            <div class="stock-actions">
                <button onclick="searchStock()" class="refresh-btn">
                    <i class="bi bi-arrow-clockwise"></i> 刷新數據
                </button>
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
    // 隱藏聊天界面和輸入區域
    document.getElementById('chat-container').style.display = 'none';
    document.getElementById('preset-questions').style.display = 'none';
    document.getElementById('input-area').style.display = 'none';

    // 顯示股票查詢界面
    document.getElementById('stock-query-container').style.display = 'block';

    // 移除歷史記錄的活躍狀態
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });

    // 清空當前對話ID
    currentConversationId = null;
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