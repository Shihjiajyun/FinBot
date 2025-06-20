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
            <p>請稍候，正在從Yahoo Finance獲取最新數據</p>
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
                displayStockInfo(data.stock_info, data.financial_data);
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

// 快速搜尋
function quickSearch(ticker) {
    document.getElementById('stock-ticker-input').value = ticker;
    searchStock();
}

// 顯示股票資訊
function displayStockInfo(stockInfo, financialData) {
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

    resultArea.innerHTML = `
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
    getTenKFiles(stockInfo.symbol).then(tenKFilesHtml => {
        document.getElementById('ten-k-files-section').innerHTML = tenKFilesHtml;
    });
}

// 獲取10-K檔案列表
function getTenKFiles(ticker) {
    const formData = new FormData();
    formData.append('action', 'get_10k_files');
    formData.append('ticker', ticker);

    return fetch('stock_api.php', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.files && data.files.length > 0) {
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
                return `
                    <div class="financial-section">
                        <h5><i class="bi bi-file-earmark-text"></i> 10-K 財報檔案</h5>
                        <div class="no-data-message">
                            <p>目前沒有找到該股票的10-K檔案</p>
                            <small>系統將持續更新財報檔案</small>
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