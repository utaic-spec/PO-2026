
# ================================================== Final Fix =================================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
import smtplib
from email.message import EmailMessage
import io
import time

# ==================================================
# 1. CONFIG & API
# ==================================================
URL = "https://yqljvjfffrthnlbyitfw.supabase.co/rest/v1/po_records"
HEADERS = {
    "apikey": "sb_secret_TfzEalDLlSQ8fvrrAuPUXg_JZeZAFLg",
    "Authorization": "Bearer sb_secret_TfzEalDLlSQ8fvrrAuPUXg_JZeZAFLg",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

SENDER_EMAIL = "siamintermoldpoalert@gmail.com"
SENDER_PASS = "dycmrqdwjclyveic" 
RECEIVER_EMAIL = "utai.c@siamintermold.com"

# ==================================================
# 2. CORE FUNCTIONS
# ==================================================
def load_data():
    try:
        res = requests.get(f"{URL}?order=timestamp.desc", headers=HEADERS)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            date_cols = ['customer_eta_date', 'date_issue_po', 'planning_production_date', 'logistic_ship_date']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.date
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def update_data(po_id, up_data):
    res = requests.patch(f"{URL}?po_id=eq.{po_id}", headers=HEADERS, json=up_data)
    return res.status_code in [200, 204]

def send_email_alert(po_id, customer, product, wait_hrs=0, is_overdue=False, extra_info=""):
    msg = EmailMessage()
    
    if is_overdue:
        # --- MODE: Overdue Alert (นับวัน + เปลี่ยนสี) ---
        days_overdue = int(wait_hrs // 24) + 1 if wait_hrs > 0 else 1
        header_color = "#8B0000" if days_overdue >= 3 else "#d93025"
        urgency_label = f"🚨 ด่วนพิเศษ ({days_overdue} วัน)" if days_overdue >= 3 else f"⚠️ งานค้าง (ครั้งที่ {days_overdue})"
        subject = f"{urgency_label}: {po_id} - {customer}"
        title_text = urgency_label
        desc_text = f"รายการ PO นี้ยังไม่ได้ลงแผนการผลิต <b>เกินกำหนด 24 ชั่วโมง</b>"
        status_row = f"<tr><td style='padding:8px;border:1px solid #ddd;'><b>จำนวนวันที่ค้าง</b></td><td style='padding:8px;border:1px solid #ddd;color:{header_color};font-weight:bold;'>{days_overdue} วัน</td></tr>"
    else:
        # --- MODE: New Registration ---
        header_color = "#1a3a8a"
        subject = f"🔔 New PO Registered: {po_id} - {customer}"
        title_text = "📣 New PO Registration Alert"
        desc_text = "มีการลงทะเบียน PO ใหม่ในระบบ กรุณาตรวจสอบและดำเนินการลงแผนการผลิต"
        status_row = f"<tr><td style='padding:8px;border:1px solid #ddd;'><b>Sales Remark</b></td><td style='padding:8px;border:1px solid #ddd;'>{extra_info}</td></tr>"

    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    html_content = f"""
    <html>
    <body style="font-family: sans-serif;">
        <div style="max-width: 600px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: {header_color}; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">{title_text}</h2>
                <p style="margin: 5px 0 0;">Siam Intermold Control System</p>
            </div>
            <div style="padding: 20px;">
                <p>เรียน ทีมที่เกี่ยวข้อง,</p>
                <p>{desc_text}</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <tr style="background-color: #f8f9fa;"><td style="padding: 8px; border: 1px solid #ddd; width: 35%;"><b>PO Number</b></td><td style="padding: 8px; border: 1px solid #ddd;">{po_id}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Customer</b></td><td style="padding: 8px; border: 1px solid #ddd;">{customer}</td></tr>
                    <tr style="background-color: #f8f9fa;"><td style="padding: 8px; border: 1px solid #ddd;"><b>Product</b></td><td style="padding: 8px; border: 1px solid #ddd;">{product}</td></tr>
                    {status_row}
                </table>
                <br>
                <div style="text-align: center;">
                    <a href="https://sim-po-2026-v2.streamlit.app/" style="background-color: {header_color}; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Acess for Update</a>
                    
                </div>
            </div>
            <div style="background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; color: #666;">
                Siam Intermold Co., Ltd. | Automated Notification System
            </div>
        </div>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.send_message(msg)
        return True
    except: return False

# ==================================================
# 3. AUTHENTICATION & UI SETUP
# ==================================================
USER_DB = {
    "director": {"pwd": "2573", "role": "admin", "name": "K.Utai"},
    "sales_admin": {"pwd": "sales2026", "role": "sales", "name": "K.Fern"},
    "logistic": {"pwd": "logistic2026", "role": "planning", "name": "K.Rung"}
}

st.set_page_config(page_title="SIM PO Master 2026", layout="wide")

if 'user' not in st.session_state:
    empty1, col_login, empty2 = st.columns([1, 1.2, 1]) 
    with col_login:
        st.write("##") 
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #1a3a8a;'>🔐 SIM Login</h2>", unsafe_allow_html=True)
            u = st.text_input("User ID")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True, type="primary"):
                if u in USER_DB and USER_DB[u]['pwd'] == p:
                    st.session_state.user = USER_DB[u]
                    st.rerun()
                else:
                    st.error("❌ ID หรือ Password ไม่ถูกต้อง")
    st.stop()

user = st.session_state.user
role = user['role']
st.title(f"📦 SIM PO Master System ({role.capitalize()})")

with st.sidebar:
    st.write(f"👤 User: **{user['name']}**")
    if st.button("Log out"):
        del st.session_state.user
        st.rerun()

allowed_tabs = ["📊 Dashboard"]
if role in ["admin", "sales"]: allowed_tabs.append("➕ Create PO")
if role in ["admin", "planning"]: 
    allowed_tabs.append("🏭 Planning Update")
    allowed_tabs.append("🚚 Logistic Update")

tabs = st.tabs(allowed_tabs)

# --- TAB: Dashboard ---
with tabs[0]:
    st.subheader("🔍 Search & Filter Console")
    df = load_data()
    
    if not df.empty:
        filtered = df.copy()
        c1, c2, c3 = st.columns(3)
        with c1:
            on_cust = st.checkbox("กรอง: Customer")
            f_cust = st.multiselect("ลูกค้า", options=sorted(df['customer'].unique()) if 'customer' in df.columns else [], disabled=not on_cust)
        with c2:
            on_prod = st.checkbox("กรอง: Product")
            f_prod = st.multiselect("สินค้า", options=sorted(df['product'].unique()) if 'product' in df.columns else [], disabled=not on_prod)
        with c3:
            on_search = st.checkbox("กรอง: PO ID")
            f_search = st.text_input("รหัส PO ID", disabled=not on_search)

        st.write("---")
        d1, d2 = st.columns(2)
        with d1:
            on_issue = st.checkbox("กรอง: Date Issue")
            # แก้ไขปัญหาวันที่ค่าว่าง
            valid_issue_dates = df['date_issue_po'].dropna()
            start_date = valid_issue_dates.min() if not valid_issue_dates.empty else date.today()
            end_date = valid_issue_dates.max() if not valid_issue_dates.empty else date.today()
            date_issue_range = st.date_input("ช่วงวันที่ออก PO", value=[start_date, end_date], disabled=not on_issue)
            
        with d2:
            on_eta = st.checkbox("กรอง: Customer ETA")
            valid_eta_dates = df['customer_eta_date'].dropna()
            start_eta = valid_eta_dates.min() if not valid_eta_dates.empty else date.today()
            end_eta = valid_eta_dates.max() if not valid_eta_dates.empty else date.today()
            eta_range = st.date_input("ช่วงวัน ETA", value=[start_eta, end_eta], disabled=not on_eta)

        # Apply Filters
        if on_cust and f_cust: filtered = filtered[filtered['customer'].isin(f_cust)]
        if on_prod and f_prod: filtered = filtered[filtered['product'].isin(f_prod)]
        if on_search and f_search: filtered = filtered[filtered['po_id'].str.contains(f_search, case=False, na=False)]
        if on_issue and isinstance(date_issue_range, list) and len(date_issue_range) == 2:
            filtered = filtered[(filtered['date_issue_po'] >= date_issue_range[0]) & (filtered['date_issue_po'] <= date_issue_range[1])]
        if on_eta and isinstance(eta_range, list) and len(eta_range) == 2:
            filtered = filtered[(filtered['customer_eta_date'] >= eta_range[0]) & (filtered['customer_eta_date'] <= eta_range[1])]

        st.divider()
        st.write(f"📊 ผลลัพธ์: **{len(filtered)}** รายการ")
        cols_to_show = ['po_id', 'customer', 'product', 'po_qty', 'part_no', 'date_issue_po', 'customer_eta_date', 'planning_production_date', 'logistic_ship_date', 'sales_remark']
        st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True)

        # --- 🚨 OVERDUE MONITORING SECTION ---
        if role in ["sales", "admin"]: 
            st.write("---")
            st.subheader("🚨 Overdue Monitoring (Pending Plan > 24 Hours)")
            
            if st.button("🚨 เช็คงานค้างและแจ้งเตือน (ค้างเกิน 24 ชม.)", use_container_width=True, type="primary"):
                with st.spinner("กำลังตรวจสอบรายการค้าง..."):
                    res = requests.get(f"{URL}?order=timestamp.desc", headers=HEADERS)
                    if res.status_code == 200:
                        df_check = pd.DataFrame(res.json())
                        pending_plan = df_check[df_check['planning_production_date'].isna()].copy()
                        
                        if pending_plan.empty:
                            st.success("✅ ไม่มี PO ค้างรอลงแผน")
                        else:
                            now_utc = datetime.utcnow()
                            today_str = date.today().isoformat()
                            overdue_sent_list = []
                            already_notified = []
                            summary = []
                            
                            for _, row in pending_plan.iterrows():
                                created_at = pd.to_datetime(row['timestamp']).replace(tzinfo=None)
                                diff_min = (now_utc - created_at).total_seconds() / 60
                                last_alert = str(row.get('last_overdue_alert_date', 'None'))
                                
                                wait_hrs = diff_min / 60
                                summary.append({"PO ID": row['po_id'], "Wait (Hrs)": round(wait_hrs, 2), "Last Alert": last_alert})
                                
                                if diff_min > 1440: # 24 Hours
                                    if last_alert != today_str:
                                        if send_email_alert(row['po_id'], row['customer'], row['product'], wait_hrs=wait_hrs, is_overdue=True):
                                            update_data(row['po_id'], {"last_overdue_alert_date": today_str})
                                            overdue_sent_list.append(row['po_id'])
                                    else:
                                        already_notified.append(row['po_id'])
                            
                            if overdue_sent_list:
                                st.error(f"⚠️ ส่งเมลแจ้งเตือนใหม่ {len(overdue_sent_list)} รายการ!")
                                st.balloons()
                            if already_notified:
                                st.info(f"ℹ️ {len(already_notified)} รายการส่งเตือนของวันนี้ไปแล้ว")
                            if not overdue_sent_list and not already_notified:
                                st.warning("⏳ ยังไม่มีรายการใดค้างเกิน 24 ชม.")
                            st.table(summary)

# --- TAB: Create PO ---
if "➕ Create PO" in allowed_tabs:
    idx = allowed_tabs.index("➕ Create PO")
    with tabs[idx]:
        st.subheader("📝 Register New Purchase Order")
        with st.form("f_create", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                p_id = st.text_input("PO ID *")
                cust = st.text_input("Customer Name *")
                prod = st.selectbox("Product", ["Mold", "Mold Part", "Mass-Part", "Other"])
                qty = st.number_input("Quantity", min_value=1)
            with c2:
                p_no = st.text_input("Part No.")
                iss = st.date_input("Date Issue PO", value=date.today())
                eta = st.date_input("Customer ETA", value=date.today())
            rem = st.text_area("Sales Remark")
            
            if st.form_submit_button("Submit & Send Email Alert"):
                if p_id and cust:
                    payload = {"po_id": p_id, "customer": cust, "product": prod, "po_qty": qty, "part_no": p_no, "date_issue_po": iss.isoformat(), "customer_eta_date": eta.isoformat(), "sales_remark": rem}
                    res = requests.post(URL, headers=HEADERS, json=payload)
                    if res.status_code in [200, 201]:
                        # แก้ไขการเรียกใช้ฟังก์ชันให้ตรงกับที่ประกาศไว้
                        email_ok = send_email_alert(p_id, cust, prod, is_overdue=False, extra_info=rem)
                        update_data(p_id, {"alert_sent": email_ok})
                        st.success("✅ บันทึกและส่งเมลแจ้งเตือนเรียบร้อย!"); time.sleep(1); st.rerun()
                else: st.warning("กรุณากรอกข้อมูล PO ID และ Customer")

# --- TAB: Planning Update ---
if "🏭 Planning Update" in allowed_tabs:
    idx = allowed_tabs.index("🏭 Planning Update")
    with tabs[idx]:
        df_p = load_data()
        if not df_p.empty:
            pending = df_p[df_p['planning_production_date'].isna()].copy()
            if not pending.empty:
                pending['display_name'] = pending.apply(lambda x: f"ID: {x['po_id']} | {x['customer']}", axis=1)
                choice_map = dict(zip(pending['display_name'], pending['po_id']))
                target_display = st.selectbox("🎯 Select PO for Planning", pending['display_name'].tolist())
                target_id = choice_map[target_display]
                with st.form("f_plan"):
                    p_date = st.date_input("Plan Finish Date")
                    p_rem = st.text_area("Planning Remark")
                    if st.form_submit_button("Update Plan"):
                        if update_data(target_id, {"planning_production_date": p_date.isoformat(), "planning_remark": p_rem}):
                            st.success("Plan Updated!"); time.sleep(1); st.rerun()
            else: st.info("✅ ไม่มีรายการค้างรอลงแผน")

# --- TAB: Logistic Update ---
if "🚚 Logistic Update" in allowed_tabs:
    idx = allowed_tabs.index("🚚 Logistic Update")
    with tabs[idx]:
        df_l = load_data()
        if not df_l.empty:
            ready = df_l[df_l['planning_production_date'].notna() & df_l['logistic_ship_date'].isna()].copy()
            if not ready.empty:
                ready['display_name'] = ready.apply(lambda x: f"ID: {x['po_id']} | Plan: {x['planning_production_date']}", axis=1)
                choice_map_l = dict(zip(ready['display_name'], ready['po_id']))
                target_display_l = st.selectbox("📦 Select PO for Shipment", ready['display_name'].tolist())
                target_id_l = choice_map_l[target_display_l]
                with st.form("f_log"):
                    l_date = st.date_input("Actual Ship Date")
                    l_rem = st.text_area("Logistic Remark")
                    if st.form_submit_button("Confirm Shipment"):
                        if update_data(target_id_l, {"logistic_ship_date": l_date.isoformat(), "logistic_remark": l_rem}):
                            st.success("Shipment Recorded!"); time.sleep(1); st.rerun()

            else: st.info("📦 ไม่มีรายการผลิตเสร็จที่รอส่ง")
