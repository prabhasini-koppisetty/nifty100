-- =====================================================================
-- NIFTY 100 EXPLORATORY ANALYTICAL QUERIES (10 QUERIES)
-- Database: nifty100.db
-- =====================================================================

-- ---------------------------------------------------------------------
-- QUERY 1: Sector Distribution & Index Weight Analysis
-- ---------------------------------------------------------------------
SELECT 
    broad_sector,
    COUNT(company_id) AS total_companies,
    ROUND(SUM(index_weight_pct), 2) AS total_sector_weight_pct
FROM sectors
GROUP BY broad_sector
ORDER BY total_sector_weight_pct DESC;


-- ---------------------------------------------------------------------
-- QUERY 2: Top 10 Companies by Market Capitalization (Latest Year)
-- ---------------------------------------------------------------------
SELECT 
    c.id AS ticker,
    c.company_name,
    m.year,
    m.market_cap_crore,
    m.enterprise_value_crore
FROM market_cap m
JOIN companies c ON m.company_id = c.id
WHERE m.year = (SELECT MAX(year) FROM market_cap)
ORDER BY m.market_cap_crore DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- QUERY 3: High Profitability Companies (ROE >= 15% and ROCE >= 15%)
-- ---------------------------------------------------------------------
SELECT 
    id AS ticker,
    company_name,
    roe_percentage,
    roce_percentage
FROM companies
WHERE roe_percentage >= 15.0 AND roce_percentage >= 15.0
ORDER BY roe_percentage DESC;


-- ---------------------------------------------------------------------
-- QUERY 4: Sales Growth Leaders (Analysis Table)
-- ---------------------------------------------------------------------
SELECT 
    a.company_id AS ticker,
    c.company_name,
    a.compounded_sales_growth,
    a.compounded_profit_growth,
    a.stock_price_cagr
FROM analysis a
JOIN companies c ON a.company_id = c.id
ORDER BY a.company_id;


-- ---------------------------------------------------------------------
-- QUERY 5: Annual Operating Profit Margin (OPM) Trend for Bluechips
-- ---------------------------------------------------------------------
SELECT 
    pl.company_id AS ticker,
    pl.year,
    pl.sales,
    pl.operating_profit,
    pl.opm_percentage
FROM profitandloss pl
WHERE pl.company_id IN ('TCS', 'INFY', 'HDFCBANK', 'RELIANCE', 'WIPRO')
ORDER BY pl.company_id, pl.year DESC;


-- ---------------------------------------------------------------------
-- QUERY 6: Balance Sheet Leverage & Asset Strength Check
-- ---------------------------------------------------------------------
SELECT 
    bs.company_id AS ticker,
    bs.year,
    bs.equity_capital,
    bs.reserves,
    bs.borrowings,
    bs.total_assets,
    ROUND(bs.borrowings / NULLIF(bs.equity_capital + bs.reserves, 0), 2) AS debt_to_equity_calc
FROM balancesheet bs
WHERE bs.year = '2024-03'
ORDER BY bs.borrowings DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- QUERY 7: Cash Flow Quality (Operating Cash Flow vs Net Profit)
-- ---------------------------------------------------------------------
SELECT 
    cf.company_id AS ticker,
    cf.year,
    cf.operating_activity AS cash_from_operations,
    pl.net_profit,
    ROUND(cf.operating_activity - pl.net_profit, 2) AS cfo_minus_net_profit
FROM cashflow cf
JOIN profitandloss pl ON cf.company_id = pl.company_id AND cf.year = pl.year
WHERE cf.year = '2024-03'
ORDER BY cash_from_operations DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- QUERY 8: Financial Valuation Ratios Summary
-- ---------------------------------------------------------------------
SELECT 
    fr.company_id AS ticker,
    fr.year,
    fr.net_profit_margin_pct,
    fr.return_on_equity_pct,
    fr.debt_to_equity,
    fr.interest_coverage,
    fr.earnings_per_share
FROM financial_ratios fr
WHERE fr.year = '2024-03'
ORDER BY fr.return_on_equity_pct DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- QUERY 9: Peer Group Breakdown & Benchmark Comparison
-- ---------------------------------------------------------------------
SELECT 
    pg.peer_group_name,
    pg.company_id AS ticker,
    c.company_name,
    pg.is_benchmark
FROM peer_groups pg
JOIN companies c ON pg.company_id = c.id
ORDER BY pg.peer_group_name, pg.is_benchmark DESC;


-- ---------------------------------------------------------------------
-- QUERY 10: Annual Report Documents Count Per Company
-- ---------------------------------------------------------------------
SELECT 
    d.company_id AS ticker,
    c.company_name,
    COUNT(d.id) AS total_annual_reports
FROM documents d
JOIN companies c ON d.company_id = c.id
GROUP BY d.company_id, c.company_name
ORDER BY total_annual_reports DESC;
