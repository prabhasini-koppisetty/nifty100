import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as gg
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.dashboard.utils.db import (
    get_all_companies,
    get_company_details,
    get_company_pl,
    get_company_bs,
    get_company_cashflow,
    get_company_ratios,
    get_company_documents,
    get_peer_groups,
    get_peer_members,
    get_sector_summary,
    run_query
)
from src.screener.engine import (
    load_screener_config,
    load_financial_data,
    run_preset,
    run_custom_screener
)
from src.analytics.peer import load_peer_mappings

# Set Page Config
st.set_page_config(
    page_title="Nifty 100 Financial Intelligence Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        background: linear-gradient(90deg, #0F172A 0%, #1E3A8A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-title {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.4rem;
    }
    .preset-card {
        background-color: #F1F5F9;
        border-left: 5px solid #1E3A8A;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# App Navigation
st.sidebar.image("https://img.icons8.com/color/96/bullish.png", width=64)
st.sidebar.title("NIFTY 100 Platform")
st.sidebar.caption("Data Intelligence & Fundamental Analysis (Sprint 3)")

nav_option = st.sidebar.radio(
    "Navigation Modules",
    [
        "📊 Platform Overview",
        "🏢 Company Profile Explorer",
        "🔍 Interactive Screener",
        "🤝 Peer Comparison Engine",
        "🏭 Sector Analytics",
        "📑 Annual Report Repository"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**System Info**")
st.sidebar.caption("Database: `nifty100.db` (SQLite)")
st.sidebar.caption("Universe: 92 Nifty 100 Companies")
st.sidebar.caption("Peer Groups: 11 Groups")

# ==========================================
# 1. OVERVIEW MODULE
# ==========================================
if nav_option == "📊 Platform Overview":
    st.markdown('<div class="main-header">Nifty 100 Financial Intelligence Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive Fundamental Analysis & Data Engineering Warehouse</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    companies_df = get_all_companies()
    total_companies = len(companies_df)
    avg_roe = companies_df['roe_percentage'].mean() if 'roe_percentage' in companies_df.columns else 0.0
    avg_roce = companies_df['roce_percentage'].mean() if 'roce_percentage' in companies_df.columns else 0.0
    
    total_pl_rows = run_query("SELECT COUNT(*) as cnt FROM profitandloss")['cnt'].iloc[0]
    total_bs_rows = run_query("SELECT COUNT(*) as cnt FROM balancesheet")['cnt'].iloc[0]
    
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Companies</div><div class="metric-value">{total_companies}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Avg ROE %</div><div class="metric-value">{avg_roe:.1f}%</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Avg ROCE %</div><div class="metric-value">{avg_roce:.1f}%</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">P&L Records</div><div class="metric-value">{total_pl_rows:,}</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="metric-card"><div class="metric-title">BS Records</div><div class="metric-value">{total_bs_rows:,}</div></div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    row1_col1, row1_col2 = st.columns([1, 1])
    
    with row1_col1:
        st.subheader("Sector Breakdown")
        sector_df = get_sector_summary()
        fig_sector = px.pie(
            sector_df, 
            values='company_count', 
            names='broad_sector',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_sector.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_sector, use_container_width=True)
        
    with row1_col2:
        st.subheader("Top 10 Companies by ROE %")
        top_roe = companies_df.nlargest(10, 'roe_percentage')[['id', 'company_name', 'broad_sector', 'roe_percentage']]
        fig_bar = px.bar(
            top_roe, 
            x='roe_percentage', 
            y='id', 
            orientation='h',
            text='roe_percentage',
            color='broad_sector',
            labels={'roe_percentage': 'ROE (%)', 'id': 'Company Ticker'},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Full Nifty 100 Company Directory")
    st.dataframe(
        companies_df[['id', 'company_name', 'broad_sector', 'sub_sector', 'face_value', 'book_value', 'roce_percentage', 'roe_percentage']],
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# 2. COMPANY PROFILE EXPLORER
# ==========================================
elif nav_option == "🏢 Company Profile Explorer":
    st.markdown('<div class="main-header">Company Profile Explorer</div>', unsafe_allow_html=True)
    
    companies_df = get_all_companies()
    ticker_list = companies_df['id'].tolist()
    
    selected_ticker = st.selectbox(
        "Select Company Ticker", 
        ticker_list,
        index=ticker_list.index("TCS") if "TCS" in ticker_list else 0
    )
    
    details = get_company_details(selected_ticker)
    
    if details:
        st.markdown(f"### {details['company_name']} ({details['id']})")
        st.caption(f"**Sector:** {details['broad_sector']} | **Sub-Sector:** {details['sub_sector']} | **Market Cap Category:** {details['market_cap_category']}")
        
        if details.get('about_company'):
            st.info(details['about_company'])
            
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Face Value", f"₹{details.get('face_value', 'N/A')}")
        c2.metric("Book Value", f"₹{details.get('book_value', 'N/A')}")
        c3.metric("Pre-computed ROCE", f"{details.get('roce_percentage', 0.0):.1f}%")
        c4.metric("Pre-computed ROE", f"{details.get('roe_percentage', 0.0):.1f}%")
        
        st.markdown("---")
        
        pl_df = get_company_pl(selected_ticker)
        bs_df = get_company_bs(selected_ticker)
        
        st.subheader("Financial Performance Trends")
        
        if not pl_df.empty:
            fig_pl = gg.Figure()
            fig_pl.add_trace(gg.Bar(x=pl_df['year'], y=pl_df['sales'], name="Sales / Revenue (Cr)"))
            fig_pl.add_trace(gg.Bar(x=pl_df['year'], y=pl_df['operating_profit'], name="Operating Profit (Cr)"))
            fig_pl.add_trace(gg.Scatter(x=pl_df['year'], y=pl_df['net_profit'], name="Net Profit (Cr)", mode='lines+markers', line=dict(color='green', width=3)))
            fig_pl.update_layout(title="Annual Sales, EBITDA & Net Profit (Crores)", barmode='group')
            st.plotly_chart(fig_pl, use_container_width=True)
            
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("Profit & Loss Statement")
            st.dataframe(pl_df, use_container_width=True, hide_index=True)
        with col_t2:
            st.subheader("Balance Sheet")
            st.dataframe(bs_df, use_container_width=True, hide_index=True)

# ==========================================
# 3. INTERACTIVE SCREENER (SPRINT 3)
# ==========================================
elif nav_option == "🔍 Interactive Screener":
    st.markdown('<div class="main-header">Sprint 3 Financial Screener Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Execute preset screeners or customize 15 financial thresholds</div>', unsafe_allow_html=True)
    
    screener_mode = st.radio("Screener Mode", ["⚡ 6 Preset Screeners", "🛠️ Custom Threshold Filtering"], horizontal=True)
    
    df_fin = load_financial_data()
    cfg = load_screener_config()
    presets_cfg = cfg.get("presets", {})
    
    if screener_mode == "⚡ 6 Preset Screeners":
        preset_names = {
            "quality_compounder": "1. Quality Compounder",
            "value_pick": "2. Value Pick",
            "growth_accelerator": "3. Growth Accelerator",
            "dividend_champion": "4. Dividend Champion",
            "debt_free_blue_chip": "5. Debt-Free Blue Chip",
            "turnaround_watch": "6. Turnaround Watch"
        }
        
        selected_key = st.selectbox("Select Preset", list(preset_names.keys()), format_func=lambda k: preset_names[k])
        preset_info = presets_cfg.get(selected_key, {})
        
        st.markdown(f"""
        <div class="preset-card">
            <h4>{preset_info.get('name', selected_key)}</h4>
            <p><strong>Description:</strong> {preset_info.get('description', '')}</p>
            <p><strong>Criteria Rules:</strong> {preset_info.get('criteria', {})}</p>
        </div>
        """, unsafe_allow_html=True)
        
        filtered_preset = run_preset(df_fin, selected_key, cfg)
        st.success(f"Matched **{len(filtered_preset)}** companies for preset **{preset_info.get('name')}**.")
        
        disp_cols = [c for c in ["company_id", "company_name", "broad_sector", "composite_quality_score", "sector_composite_quality_score", "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr", "revenue_cagr_5yr", "pe_ratio", "pb_ratio", "dividend_yield_pct"] if c in filtered_preset.columns]
        
        st.dataframe(filtered_preset[disp_cols], use_container_width=True, hide_index=True)
        
    else:
        st.subheader("Custom Threshold Filter (15 Metrics)")
        with st.form("custom_screener_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                roe_min = st.number_input("Min ROE %", value=0.0, step=1.0)
                de_max = st.number_input("Max D/E Ratio (Financials skip)", value=5.0, step=0.1)
                fcf_min = st.number_input("Min FCF (₹ Cr)", value=-10000.0, step=100.0)
                rev_cagr_min = st.number_input("Min Rev CAGR 5yr %", value=-50.0, step=1.0)
                pat_cagr_min = st.number_input("Min PAT CAGR 5yr %", value=-50.0, step=1.0)
            with c2:
                opm_min = st.number_input("Min OPM %", value=-50.0, step=1.0)
                pe_max = st.number_input("Max P/E Ratio", value=200.0, step=5.0)
                pb_max = st.number_input("Max P/B Ratio", value=50.0, step=1.0)
                div_yield_min = st.number_input("Min Dividend Yield %", value=0.0, step=0.5)
                icr_min = st.number_input("Min ICR (Debt Free passes)", value=0.0, step=0.5)
            with c3:
                mcap_min = st.number_input("Min Market Cap (₹ Cr)", value=0.0, step=1000.0)
                net_prof_min = st.number_input("Min Net Profit (₹ Cr)", value=-10000.0, step=100.0)
                eps_cagr_min = st.number_input("Min EPS CAGR 5yr %", value=-50.0, step=1.0)
                asset_turn_min = st.number_input("Min Asset Turnover", value=0.0, step=0.1)
                sales_min = st.number_input("Min Sales (₹ Cr)", value=0.0, step=500.0)
                
            submitted = st.form_submit_button("Run Custom Screener")
            
        if submitted:
            custom_filters = {}
            if roe_min > 0: custom_filters["roe_min"] = roe_min
            if de_max < 5.0: custom_filters["de_max"] = de_max
            if fcf_min > -10000.0: custom_filters["fcf_min"] = fcf_min
            if rev_cagr_min > -50.0: custom_filters["revenue_cagr_5yr_min"] = rev_cagr_min
            if pat_cagr_min > -50.0: custom_filters["pat_cagr_5yr_min"] = pat_cagr_min
            if opm_min > -50.0: custom_filters["opm_min"] = opm_min
            if pe_max < 200.0: custom_filters["pe_max"] = pe_max
            if pb_max < 50.0: custom_filters["pb_max"] = pb_max
            if div_yield_min > 0: custom_filters["dividend_yield_min"] = div_yield_min
            if icr_min > 0: custom_filters["icr_min"] = icr_min
            if mcap_min > 0: custom_filters["market_cap_min"] = mcap_min
            if net_prof_min > -10000.0: custom_filters["net_profit_min"] = net_prof_min
            if eps_cagr_min > -50.0: custom_filters["eps_cagr_min"] = eps_cagr_min
            if asset_turn_min > 0: custom_filters["asset_turnover_min"] = asset_turn_min
            if sales_min > 0: custom_filters["sales_min"] = sales_min
            
            filtered_custom = run_custom_screener(df_fin, custom_filters)
            st.success(f"Matched **{len(filtered_custom)}** companies for custom criteria.")
            disp_cols = [c for c in ["company_id", "company_name", "broad_sector", "composite_quality_score", "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr", "pe_ratio", "sales"] if c in filtered_custom.columns]
            st.dataframe(filtered_custom[disp_cols], use_container_width=True, hide_index=True)

# ==========================================
# 4. PEER COMPARISON ENGINE (SPRINT 3)
# ==========================================
elif nav_option == "🤝 Peer Comparison Engine":
    st.markdown('<div class="main-header">Peer Comparison & Radar Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Evaluate company percentiles and polar radar charts across 11 peer groups</div>', unsafe_allow_html=True)
    
    df_peers = load_peer_mappings()
    peer_group_list = sorted(df_peers['peer_group_name'].unique())
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        selected_pg = st.selectbox("Select Peer Group", peer_group_list)
        pg_members = df_peers[df_peers['peer_group_name'] == selected_pg]
        member_cids = pg_members['company_id'].tolist()
        
        selected_cid = st.selectbox("Select Company to View Radar", member_cids)
        
    with col_p2:
        radar_img_path = ROOT_DIR / "reports" / "radar_charts" / f"{selected_cid}_radar.png"
        if radar_img_path.exists():
            st.image(str(radar_img_path), caption=f"8-Axis Polar Radar Chart for {selected_cid}", width=450)
        else:
            st.info(f"Radar chart for {selected_cid} is available after running peer engine.")
            
    st.markdown("---")
    st.subheader(f"Peer Group Percentiles: {selected_pg}")
    
    percentile_df = run_query("""
        SELECT company_id, metric, value, percentile_rank, year
        FROM peer_percentiles
        WHERE peer_group_name = ?
        ORDER BY company_id ASC, metric ASC
    """, (selected_pg,))
    
    if not percentile_df.empty:
        st.dataframe(percentile_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No peer percentiles found for this group. Run peer.py to populate.")

# ==========================================
# 5. SECTOR ANALYTICS
# ==========================================
elif nav_option == "🏭 Sector Analytics":
    st.markdown('<div class="main-header">Sector Analytics</div>', unsafe_allow_html=True)
    
    sector_summary = get_sector_summary()
    
    fig_sector_bar = px.bar(
        sector_summary,
        x='broad_sector',
        y='avg_roe',
        color='company_count',
        title="Average ROE % by Sector",
        labels={'broad_sector': 'Sector', 'avg_roe': 'Average ROE (%)'}
    )
    st.plotly_chart(fig_sector_bar, use_container_width=True)
    st.dataframe(sector_summary, use_container_width=True, hide_index=True)

# ==========================================
# 6. ANNUAL REPORT REPOSITORY
# ==========================================
elif nav_option == "📑 Annual Report Repository":
    st.markdown('<div class="main-header">Annual Report Repository</div>', unsafe_allow_html=True)
    
    docs_df = run_query("""
        SELECT d.company_id, c.company_name, d.year, d.annual_report 
        FROM documents d 
        JOIN companies c ON d.company_id = c.id 
        ORDER BY d.year DESC, d.company_id ASC
        LIMIT 100
    """)
    st.dataframe(docs_df, use_container_width=True, hide_index=True)
