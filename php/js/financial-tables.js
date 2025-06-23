// 財務表格生成相關函數

// 格式化數字（通用）
function formatNumber(num) {
    if (num === null || num === undefined || num === '' || num === 'N/A') return 'N/A';
    
    const numValue = parseFloat(num);
    if (isNaN(numValue)) return 'N/A';
    
    if (numValue >= 1e12) return (numValue / 1e12).toFixed(2) + 'T';
    if (numValue >= 1e9) return (numValue / 1e9).toFixed(2) + 'B';
    if (numValue >= 1e6) return (numValue / 1e6).toFixed(2) + 'M';
    if (numValue >= 1e3) return (numValue / 1e3).toFixed(2) + 'K';
    return numValue.toLocaleString();
}

// 格式化增長率
function formatGrowthRate(rate) {
    if (rate === null || rate === undefined || rate === '') {
        return '<span class="na-value">N/A</span>';
    }
    const numRate = parseFloat(rate);
    if (isNaN(numRate)) {
        return '<span class="na-value">N/A</span>';
    }
    const sign = numRate >= 0 ? '+' : '';
    return `${sign}${numRate.toFixed(2)}%`;
}

// 獲取增長率的CSS類別
function getGrowthClass(rate) {
    if (rate === null || rate === undefined || rate === '') {
        return 'neutral';
    }
    const numRate = parseFloat(rate);
    if (isNaN(numRate)) {
        return 'neutral';
    }
    if (numRate > 10) return 'very-positive';
    if (numRate > 0) return 'positive';
    if (numRate > -10) return 'slightly-negative';
    return 'negative';
}

// 格式化財務數值（百萬美元）
function formatFinancialValue(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    return `$${formatNumber(numValue)}M`;
}

// 格式化每股盈餘
function formatEPS(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    return `$${numValue.toFixed(2)}`;
}

// 格式化股數（百萬股）
function formatShares(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    return `${formatNumber(numValue)}M`;
}

// 格式化比率
function formatRatio(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    return `${numValue.toFixed(2)}%`;
}

// 獲取利潤率的CSS類別
function getMarginClass(value) {
    if (value === null || value === undefined || value === '') return 'neutral';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return 'neutral';
    if (numValue > 20) return 'very-positive';
    if (numValue > 10) return 'positive';
    if (numValue > 0) return 'slightly-positive';
    return 'negative';
}

// 獲取財務數值的CSS類別（基於數值大小）
function getFinancialValueClass(value, type = 'revenue') {
    if (value === null || value === undefined || value === '') return 'neutral';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return 'neutral';

    // 根據不同類型設定不同的閾值
    switch (type) {
        case 'revenue':
        case 'gross_profit':
        case 'operating_income':
        case 'net_income':
            if (numValue > 100000) return 'very-positive'; // 超過1000億
            if (numValue > 50000) return 'positive'; // 超過500億
            if (numValue > 10000) return 'slightly-positive'; // 超過100億
            if (numValue > 0) return 'neutral';
            return 'negative';
        case 'eps':
            if (numValue > 10) return 'very-positive';
            if (numValue > 5) return 'positive';
            if (numValue > 2) return 'slightly-positive';
            if (numValue > 0) return 'neutral';
            return 'negative';
        case 'shares':
            if (numValue < 1000) return 'very-positive'; // 股數少通常更好
            if (numValue < 5000) return 'positive';
            if (numValue < 10000) return 'slightly-positive';
            return 'neutral';
        default:
            return 'neutral';
    }
}

// 獲取ROA/ROE等比率的CSS類別
function getRatioClass(value, type = 'general') {
    if (value === null || value === undefined || value === '') return 'neutral';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return 'neutral';

    switch (type) {
        case 'roa':
        case 'roe':
        case 'roic':
            if (numValue > 15) return 'very-positive';
            if (numValue > 10) return 'positive';
            if (numValue > 5) return 'slightly-positive';
            if (numValue > 0) return 'neutral';
            return 'negative';
        case 'debt_ratio':
            if (numValue > 2) return 'negative';
            if (numValue > 1) return 'slightly-negative';
            if (numValue > 0.5) return 'neutral';
            if (numValue > 0.3) return 'slightly-positive';
            return 'positive';
        case 'current_ratio':
            if (numValue > 2) return 'very-positive';
            if (numValue > 1.5) return 'positive';
            if (numValue > 1) return 'slightly-positive';
            if (numValue > 0.8) return 'neutral';
            return 'negative';
        case 'debt_payoff':
            if (numValue < 3) return 'very-positive';
            if (numValue < 5) return 'positive';
            if (numValue < 10) return 'slightly-positive';
            if (numValue < 20) return 'neutral';
            return 'negative';
        default:
            return 'neutral';
    }
}

// 格式化年數
function formatYears(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    if (numValue === Infinity || numValue > 999) return '<span class="na-value">∞</span>';
    return `${numValue.toFixed(1)}年`;
}

// 格式化倍數
function formatMultiple(value) {
    if (value === null || value === undefined || value === '') return '<span class="na-value">N/A</span>';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return '<span class="na-value">N/A</span>';
    return `${numValue.toFixed(2)}x`;
}

// 生成財務增長率表格（縱向年份布局）
function generateVerticalGrowthTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => b - a); // 最新年份在前
    const metrics = [
        {key: 'equity_growth', label: '股東權益成長率 (%)'},
        {key: 'net_income_growth', label: '淨利成長率 (%)'},
        {key: 'cash_flow_growth', label: '現金流成長率 (%)'},
        {key: 'revenue_growth', label: '營收成長率 (%)'}
    ];

    return `
        <table class="financial-table vertical-years">
            <thead>
                <tr>
                    <th>年份</th>
                    ${metrics.map(metric => `<th>${metric.label}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${years.map(year => {
                    const yearData = data.find(item => item.year === year);
                    return `
                        <tr>
                            <td class="year-cell">${year}</td>
                            ${metrics.map(metric => {
                                const value = yearData ? yearData[metric.key] : null;
                                return `<td class="growth-cell ${getGrowthClass(value)}">${formatGrowthRate(value)}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// 生成財務絕對數值表格（縱向年份布局）
function generateVerticalAbsoluteMetricsTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => b - a);

    // 分組顯示
    const absoluteMetrics = [
        {key: 'revenue', label: '營收'},
        {key: 'cogs', label: '銷貨成本'},
        {key: 'gross_profit', label: '毛利'},
        {key: 'operating_income', label: '營業收入'},
        {key: 'operating_expenses', label: '營業費用'},
        {key: 'income_before_tax', label: '稅前收入'},
        {key: 'net_income', label: '淨利'},
        {key: 'eps_basic', label: '每股盈餘 ($)'},
        {key: 'outstanding_shares', label: '流通股數 (M)'}
    ];

    const ratioMetrics = [
        {key: 'net_income_margin', label: '淨利率 (%)'},
        {key: 'gross_margin', label: '毛利率 (%)'},
        {key: 'operating_margin', label: '營業利潤率 (%)'}
    ];

    const allMetrics = [...absoluteMetrics, ...ratioMetrics];

    return `
        <table class="financial-table vertical-years">
            <thead>
                <tr>
                    <th>年份</th>
                    ${allMetrics.map(metric => `<th>${metric.label}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${years.map(year => {
                    const yearData = data.find(item => item.year === year);
                    return `
                        <tr>
                            <td class="year-cell">${year}</td>
                            ${allMetrics.map(metric => {
                                const value = yearData ? yearData[metric.key] : null;
                                
                                let formattedValue;
                                let valueClass;
                                
                                if (metric.key === 'eps_basic') {
                                    formattedValue = formatEPS(value);
                                    valueClass = getFinancialValueClass(value, 'eps');
                                } else if (metric.key === 'outstanding_shares') {
                                    formattedValue = formatShares(value);
                                    valueClass = getFinancialValueClass(value, 'shares');
                                } else if (ratioMetrics.includes(metric)) {
                                    formattedValue = formatRatio(value);
                                    valueClass = getMarginClass(value);
                                } else {
                                    formattedValue = formatFinancialValue(value);
                                    valueClass = getFinancialValueClass(value, metric.key.includes('income') ? 'net_income' : 'revenue');
                                }
                                
                                return `<td class="${ratioMetrics.includes(metric) ? 'ratio-cell' : 'financial-value'} ${valueClass}">${formattedValue}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// 生成資產負債表數據表格（縱向年份布局）
function generateVerticalBalanceSheetTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => b - a);

    const assetMetrics = [
        {key: 'current_assets', label: '流動資產'},
        {key: 'total_assets', label: '總資產'},
        {key: 'current_liabilities', label: '流動負債'},
        {key: 'total_liabilities', label: '總負債'},
        {key: 'long_term_debt', label: '長期負債'},
        {key: 'retained_earnings', label: '保留盈餘'},
        {key: 'shareholders_equity', label: '股東權益'}
    ];

    const ratioMetrics = [
        {key: 'book_value_per_share', label: '每股帳面價值 ($)'},
        {key: 'roa', label: 'ROA (%)'},
        {key: 'roe', label: 'ROE (%)'},
        {key: 'roic', label: 'ROIC (%)'},
        {key: 'debt_equity_ratio', label: '負債股權比'},
        {key: 'debt_payoff_years', label: '債務償還年限'},
        {key: 'current_ratio', label: '流動比率'}
    ];

    const allMetrics = [...assetMetrics, ...ratioMetrics];

    return `
        <table class="financial-table vertical-years">
            <thead>
                <tr>
                    <th>年份</th>
                    ${allMetrics.map(metric => `<th>${metric.label}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${years.map(year => {
                    const yearData = data.find(item => item.year === year);
                    return `
                        <tr>
                            <td class="year-cell">${year}</td>
                            ${allMetrics.map(metric => {
                                const value = yearData ? yearData[metric.key] : null;
                                
                                let formattedValue;
                                let valueClass;
                                
                                if (assetMetrics.includes(metric)) {
                                    formattedValue = formatFinancialValue(value);
                                    valueClass = getFinancialValueClass(value, 'revenue');
                                } else if (metric.key === 'book_value_per_share') {
                                    formattedValue = formatEPS(value);
                                    valueClass = getRatioClass(value, 'general');
                                } else if (metric.key === 'roa' || metric.key === 'roe' || metric.key === 'roic') {
                                    formattedValue = formatRatio(value);
                                    valueClass = getRatioClass(value, metric.key);
                                } else if (metric.key === 'debt_equity_ratio' || metric.key === 'current_ratio') {
                                    formattedValue = formatMultiple(value);
                                    valueClass = getRatioClass(value, metric.key);
                                } else if (metric.key === 'debt_payoff_years') {
                                    formattedValue = formatYears(value);
                                    valueClass = getRatioClass(value, 'debt_payoff');
                                } else {
                                    formattedValue = formatRatio(value);
                                    valueClass = getRatioClass(value, 'general');
                                }
                                
                                return `<td class="${assetMetrics.includes(metric) ? 'financial-value' : 'ratio-cell'} ${valueClass}">${formattedValue}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// 生成財務增長率表格（橫向年份布局 - 項目縱向，年份橫向）
function generateHorizontalGrowthTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => a - b); // 年份從舊到新
    const metrics = [
        {key: 'revenue_growth', label: '營收成長率 (%)'},
        {key: 'net_income_growth', label: '淨利成長率 (%)'},
        {key: 'cash_flow_growth', label: '現金流成長率 (%)'},
        {key: 'equity_growth', label: '股東權益成長率 (%)'}
    ];

    return `
        <table class="financial-table horizontal-years">
            <thead>
                <tr>
                    <th>項目</th>
                    ${years.map(year => `<th>${year}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${metrics.map(metric => {
                    return `
                        <tr>
                            <td class="metric-label">${metric.label}</td>
                            ${years.map(year => {
                                const yearData = data.find(item => item.year === year);
                                const value = yearData ? yearData[metric.key] : null;
                                return `<td class="growth-cell ${getGrowthClass(value)}">${formatGrowthRate(value)}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// 生成財務絕對數值表格（橫向年份布局）
function generateHorizontalAbsoluteMetricsTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => a - b);

    // 分組顯示
    const absoluteMetrics = [
        {key: 'revenue', label: '營收'},
        {key: 'cogs', label: '銷貨成本'},
        {key: 'gross_profit', label: '毛利'},
        {key: 'operating_income', label: '營業收入'},
        {key: 'operating_expenses', label: '營業費用'},
        {key: 'income_before_tax', label: '稅前收入'},
        {key: 'net_income', label: '淨利'},
        {key: 'eps_basic', label: '每股盈餘 ($)'},
        {key: 'outstanding_shares', label: '流通股數 (M)'}
    ];

    const ratioMetrics = [
        {key: 'net_income_margin', label: '淨利率 (%)'},
        {key: 'gross_margin', label: '毛利率 (%)'},
        {key: 'operating_margin', label: '營業利潤率 (%)'}
    ];

    const allMetrics = [...absoluteMetrics, ...ratioMetrics];

    return `
        <table class="financial-table horizontal-years">
            <thead>
                <tr>
                    <th>項目</th>
                    ${years.map(year => `<th>${year}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${allMetrics.map(metric => {
                    return `
                        <tr>
                            <td class="metric-label">${metric.label}</td>
                            ${years.map(year => {
                                const yearData = data.find(item => item.year === year);
                                const value = yearData ? yearData[metric.key] : null;
                                
                                let formattedValue;
                                let valueClass;
                                
                                if (metric.key === 'eps_basic') {
                                    formattedValue = formatEPS(value);
                                    valueClass = getFinancialValueClass(value, 'eps');
                                } else if (metric.key === 'outstanding_shares') {
                                    formattedValue = formatShares(value);
                                    valueClass = getFinancialValueClass(value, 'shares');
                                } else if (ratioMetrics.includes(metric)) {
                                    formattedValue = formatRatio(value);
                                    valueClass = getMarginClass(value);
                                } else {
                                    formattedValue = formatFinancialValue(value);
                                    valueClass = getFinancialValueClass(value, metric.key.includes('income') ? 'net_income' : 'revenue');
                                }
                                
                                return `<td class="${ratioMetrics.includes(metric) ? 'ratio-cell' : 'financial-value'} ${valueClass}">${formattedValue}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// 生成資產負債表數據表格（橫向年份布局）
function generateHorizontalBalanceSheetTable(data) {
    if (!data || data.length === 0) return '';

    const years = data.map(item => item.year).sort((a, b) => a - b);

    const assetMetrics = [
        {key: 'current_assets', label: '流動資產'},
        {key: 'total_assets', label: '總資產'},
        {key: 'current_liabilities', label: '流動負債'},
        {key: 'total_liabilities', label: '總負債'},
        {key: 'long_term_debt', label: '長期負債'},
        {key: 'retained_earnings', label: '保留盈餘'},
        {key: 'shareholders_equity', label: '股東權益'}
    ];

    const ratioMetrics = [
        {key: 'book_value_per_share', label: '每股帳面價值 ($)'},
        {key: 'roa', label: 'ROA (%)'},
        {key: 'roe', label: 'ROE (%)'},
        {key: 'roic', label: 'ROIC (%)'},
        {key: 'debt_equity_ratio', label: '負債股權比'},
        {key: 'debt_payoff_years', label: '債務償還年限'},
        {key: 'current_ratio', label: '流動比率'}
    ];

    const allMetrics = [...assetMetrics, ...ratioMetrics];

    return `
        <table class="financial-table horizontal-years">
            <thead>
                <tr>
                    <th>項目</th>
                    ${years.map(year => `<th>${year}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${allMetrics.map(metric => {
                    return `
                        <tr>
                            <td class="metric-label">${metric.label}</td>
                            ${years.map(year => {
                                const yearData = data.find(item => item.year === year);
                                const value = yearData ? yearData[metric.key] : null;
                                
                                let formattedValue;
                                let valueClass;
                                
                                if (assetMetrics.includes(metric)) {
                                    formattedValue = formatFinancialValue(value);
                                    valueClass = getFinancialValueClass(value, 'revenue');
                                } else if (metric.key === 'book_value_per_share') {
                                    formattedValue = formatEPS(value);
                                    valueClass = getRatioClass(value, 'general');
                                } else if (metric.key === 'roa' || metric.key === 'roe' || metric.key === 'roic') {
                                    formattedValue = formatRatio(value);
                                    valueClass = getRatioClass(value, metric.key);
                                } else if (metric.key === 'debt_equity_ratio' || metric.key === 'current_ratio') {
                                    formattedValue = formatMultiple(value);
                                    valueClass = getRatioClass(value, metric.key);
                                } else if (metric.key === 'debt_payoff_years') {
                                    formattedValue = formatYears(value);
                                    valueClass = getRatioClass(value, 'debt_payoff');
                                } else {
                                    formattedValue = formatRatio(value);
                                    valueClass = getRatioClass(value, 'general');
                                }
                                
                                return `<td class="${assetMetrics.includes(metric) ? 'financial-value' : 'ratio-cell'} ${valueClass}">${formattedValue}</td>`;
                            }).join('')}
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
} 