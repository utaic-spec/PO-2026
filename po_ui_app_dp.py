import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import smtplib
from email.message import EmailMessage
import time
import json

# ==================================================
# 1. INITIALIZE & CONFIG
# ==================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

st.set_page_config(page_title="PO Master 2026 - Siam Intermold", layout="wide")

# --- CONFIG FOR DEPLOY ---
SPREADSHEET_ID = "1dHa3wGMvEgZdkKiE8T2J9nzQmfoDTF3AnLWah-RcTWU"
SHEET_NAME = "PO2026"

# ดึงข้อมูลจาก Streamlit Secrets เมื่อ Deploy ขึ้น Cloud
SENDER_EMAIL = st.secrets["email"]["SENDER_EMAIL"]
SENDER_APP_PASSWORD = st.secrets["email"]["SENDER_APP_PASSWORD"]
ALERT_RECEIVER = st.secrets["email"]["ALERT_RECEIVER"]

# ==================================================
# 2. CORE FUNCTIONS
# ==================================================

def get_ss_with_retry(retries=3):
    for i in range(retries):
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            # ปรับให้ดึง Credentials จาก Secrets แทนไฟล์ json
            creds_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
        except Exception as e:
            time.sleep(1)
    return None

def load_data():
    try:
        ss = get_ss_with_retry()
        ws = ss.worksheet(SHEET_NAME)
        return pd.DataFrame(ws.get_all_records())
    except:
        return pd.DataFrame()

def update_po_record(po_id, col_name, val):
    try:
        ss = get_ss_with_retry()
        ws = ss.worksheet(SHEET_NAME)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        row_idx = df[df["PO ID"].astype(str) == str(po_id)].index[0] + 2
        headers = ws.row_values(1)
        col_idx = headers.index(col_name) + 1
        ws.update_cell(row_idx, col_idx, str(val))
        return True
    except Exception as e:
        st.error(f"Error updating record: {e}")
        return False

def send_full_alert(po_id=None, cust=None, product_type=None, part_no=None, qty=None, eta=None, issue_date=None, remark=None):
    # ปรับ URL ให้ดึงจากที่ระบบใช้งานจริงโดยอัตโนมัติ
    try:
        msg = EmailMessage()
        msg['Subject'] = f"📣 Notification: New PO Created - {po_id} [{cust}]"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECEIVER)
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #1E3A8A; padding: 15px; text-align: center; color: white;">
                        <h2 style="margin:0;">📣 New PO Registration</h2>
                    </div>
                    <div style="padding: 20px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #f8f9fa;"><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">PO Number</td><td style="padding:10px; border:1px solid #ddd;">{po_id}</td></tr>
                            <tr><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Customer</td><td style="padding:10px; border:1px solid #ddd;">{cust}</td></tr>
                            <tr style="background-color: #fff4e6;"><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Date Issue PO</td><td style="padding:10px; border:1px solid #ddd; color: #d9480f; font-weight:bold;">{issue_date}</td></tr>
                            <tr style="background-color: #eef2ff;"><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Product Type</td><td style="padding:10px; border:1px solid #ddd;">{product_type}</td></tr>
                            <tr><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Part Number</td><td style="padding:10px; border:1px solid #ddd;">{part_no}</td></tr>
                            <tr style="background-color: #f8f9fa;"><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Quantity</td><td style="padding:10px; border:1px solid #ddd;">{qty} Units</td></tr>
                            <tr><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Customer ETA</td><td style="padding:10px; border:1px solid #ddd;">{eta}</td></tr>
                        </table>
                        <div style="margin-top:20px; padding:10px; background-color:#fff9db; border-left:4px solid #fab005;">
                            <strong>Sales Remark:</strong> {remark if remark else '-'}
                        </div>
                        <div style="margin-top: 30px; text-align: center;">
                            <p>โปรดตรวจสอบข้อมูลในระบบ PO Master 2026</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
        return True
    except: return False

def send_reminder_email(items):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"⚠️ REMINDER: Pending PO Update (>24 Hours)"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECEIVER)
        table_rows = ""
        for item in items:
            table_rows += f"<tr><td style='padding:8px; border:1px solid #ddd;'>{item['PO ID']}</td><td style='padding:8px; border:1px solid #ddd;'>{item['Customer']}</td><td style='padding:8px; border:1px solid #ddd;'>{item['Entry Time']}</td><td style='padding:8px; border:1px solid #ddd; color:red;'>{item['Status']}</td></tr>"
        
        html_content = f"<html><body><h3 style='color: #d32f2f;'>รายการ PO ค้าง Update เกิน 24 ชม.</h3><table style='width: 100%; border-collapse: collapse;' border='1'>{table_rows}</table></body></html>"
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
        return True
    except: return False

def check_and_send_reminders():
    try:
        df_all = load_data()
        if df_all.empty: return False
        now = datetime.now()
        pending_list = []
        for index, row in df_all.iterrows():
            ts_str = str(row.get('Timestamp', '')).strip()
            plan_date = str(row.get('Planning-Production-Date', '')).strip()
            ship_date = str(row.get('Logistic-Ship-Date', '')).strip()
            if ts_str:
                try:
                    ts_dt = pd.to_datetime(ts_str)
                    if (now - ts_dt).total_seconds() / 3600 >= 24 and (plan_date == "" or ship_date == ""):
                        pending_list.append({"PO ID": row['PO ID'], "Customer": row['Customer'], "Entry Time": ts_str, "Status": "Pending"})
                except: continue
        if pending_list:
            send_reminder_email(pending_list)
            return True
    except: return False

def should_send_today():
    try:
        ss = get_ss_with_retry()
        try:
            ws = ss.worksheet("Config")
        except:
            ws = ss.add_worksheet(title="Config", rows="1", cols="2")
            ws.update_cell(1, 1, "Last-Reminder-Date")
        last_date = ws.cell(1, 2).value
        today_str = str(date.today())
        if last_date != today_str:
            ws.update_cell(1, 2, today_str)
            return True
        return False
    except: return False

# ==================================================
# 3. LOGIN INTERFACE
# ==================================================
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try:
            st.image('SIM-LOGO.jpg', width=658)
        except:
            st.warning("Logo file not found.")
        with st.container(border=True):
            st.markdown("<h4 style='text-align: center;'>Siam Inter Mold: PO Tracker Application 2026</h4>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>Log In</h2>", unsafe_allow_html=True)
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.button("Log In", use_container_width=True, type="primary"):
                ss = get_ss_with_retry()
                if ss:
                    ws_u = ss.worksheet("Users")
                    df_u = pd.DataFrame(ws_u.get_all_values())
                    df_u.columns = [h.strip() for h in df_u.iloc[0]]
                    df_u = df_u[1:]
                    match = df_u[(df_u['Email'].str.strip().str.lower() == em.strip().lower()) & (df_u['Password'].str.strip() == pw)]
                    if not match.empty:
                        st.session_state.authenticated = True
                        st.session_state.user_info = match.iloc[0].to_dict()
                        st.rerun()
                    else: st.error("Email หรือ Password ไม่ถูกต้อง")
        st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>© 2026 Siam Intermold Co., Ltd. All Rights Reserved.</p>", unsafe_allow_html=True)
    st.stop()

# ==================================================
# 4. MAIN CONTENT
# ==================================================
if st.session_state.authenticated:
    if 'reminder_checked' not in st.session_state:
        if should_send_today():
            with st.spinner("Processing Daily Reminder..."):
                check_and_send_reminders()
        st.session_state.reminder_checked = True

    user = st.session_state.user_info
    role = str(user.get('Role', '')).strip().lower()
    u_name = str(user.get('Name', '')).strip()

    with st.sidebar:
        st.info(f"👤 {u_name} ({role})")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    pages = ["📊 View Database"]
    if role in ["admin", "sales", "sale"]: pages.append("➕ Create PO")
    if role in ["admin", "planning"] or u_name == "K.Rung": pages.append("🏭 Planning")
    if role in ["admin", "logistic", "logistics"] or u_name == "K.Rung": pages.append("🚚 Logistic")

    tabs = st.tabs(pages)

    for i, page_name in enumerate(pages):
        with tabs[i]:
            df_all = load_data()
            show_cols = ["PO ID", "Customer", "Product", "PO-Qty", "Part No", "Customer-ETA-Date", "Date-Issue-PO", "Sales-Remark", "Planning-Production-Date", "Planning-Remark", "Logistic-Ship-Date", "Logistic-Remark"]
            existing = [c for c in show_cols if c in df_all.columns]

            if page_name == "📊 View Database":
                st.header("📊 Purchase Order Database")
                if not df_all.empty:
                    with st.expander("🔍 Filter Options", expanded=True):
                        f1, f2, f3 = st.columns(3)
                        sel_cust = f1.selectbox("Customer", ["All"] + sorted(df_all['Customer'].unique().tolist()))
                        f_issue_active = f2.checkbox("Filter by Issue Date Range")
                        issue_range = f2.date_input("Issue Date", [date.today(), date.today()], key="issue_filter") if f_issue_active else None
                        f_eta_active = f3.checkbox("Filter by ETA Date Range")
                        eta_range = f3.date_input("ETA Date", [date.today(), date.today()], key="eta_filter") if f_eta_active else None

                    df_f = df_all.copy()
                    if sel_cust != "All": df_f = df_f[df_f['Customer'] == sel_cust]
                    if f_issue_active and issue_range and len(issue_range) == 2:
                        df_f['tmp_issue'] = pd.to_datetime(df_f['Date-Issue-PO']).dt.date
                        df_f = df_f[(df_f['tmp_issue'] >= issue_range[0]) & (df_f['tmp_issue'] <= issue_range[1])]
                    if f_eta_active and eta_range and len(eta_range) == 2:
                        df_f['tmp_eta'] = pd.to_datetime(df_f['Customer-ETA-Date']).dt.date
                        df_f = df_f[(df_f['tmp_eta'] >= eta_range[0]) & (df_f['tmp_eta'] <= eta_range[1])]

                    st.subheader(f"📂 Result: {len(df_f)} Records")
                    st.dataframe(df_f[existing], use_container_width=True, hide_index=True)

            elif page_name == "➕ Create PO":
                st.header("➕ Create New Purchase Order")
                with st.form("f_create", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    p_id = c1.text_input("PO ID *")
                    cst = c1.text_input("Customer *")
                    ptype = c1.selectbox("Product Type", ["Mold", "Mold-Part", "Mold-Repair", "Mass-Part", "Other"])
                    iss_date = c2.date_input("Date-Issue-PO *", date.today())
                    pt_no = c2.text_input("Part No")
                    qty = c2.number_input("Qty", min_value=1)
                    eta = c2.date_input("Customer-ETA-Date", date.today())
                    rmk = st.text_area("Sales Remark")
                    
                    if st.form_submit_button("Save & Send Alert"):
                        if p_id and cst:
                            ws = get_ss_with_retry().worksheet(SHEET_NAME)
                            headers = ws.row_values(1)
                            row_data = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "PO ID": p_id, "Customer": cst, "Product": ptype, "Part No": pt_no, "PO-Qty": qty, "Customer-ETA-Date": str(eta), "Date-Issue-PO": str(iss_date), "Sales-Remark": rmk}
                            ws.append_row([row_data.get(h, "") for h in headers], value_input_option='USER_ENTERED')
                            send_full_alert(po_id=p_id, cust=cst, product_type=ptype, part_no=pt_no, qty=qty, eta=str(eta), issue_date=str(iss_date), remark=rmk)
                            st.success(f"✅ PO {p_id} Saved!"); time.sleep(1); st.rerun()
                        else: st.error("กรุณากรอกข้อมูลสำคัญ")

            elif page_name == "🏭 Planning":
                st.header("🏭 Planning Update")
                df_p = df_all[df_all['Planning-Production-Date'] == ""]
                st.dataframe(df_p[existing], use_container_width=True, hide_index=True)
                if not df_p.empty:
                    with st.form("p_up"):
                        p_target = st.selectbox("Select PO ID", df_p['PO ID'].tolist())
                        p_date = st.date_input("Production Date")
                        p_rmk = st.text_input("Note")
                        if st.form_submit_button("Update Planning"):
                            update_po_record(p_target, "Planning-Production-Date", str(p_date))
                            update_po_record(p_target, "Planning-Remark", p_rmk)
                            st.success("Updated!"); time.sleep(1); st.rerun()

            elif page_name == "🚚 Logistic":
                st.header("🚚 Logistic Update")
                df_l = df_all[(df_all['Planning-Production-Date'] != "") & (df_all['Logistic-Ship-Date'] == "")]
                st.dataframe(df_l[existing], use_container_width=True, hide_index=True)
                if not df_l.empty:
                    with st.form("l_up"):
                        l_target = st.selectbox("Select PO ID", df_l['PO ID'].tolist())
                        l_date = st.date_input("Ship Date")
                        l_rmk = st.text_input("Note")
                        if st.form_submit_button("Update Logistic"):
                            update_po_record(l_target, "Logistic-Ship-Date", str(l_date))
                            update_po_record(l_target, "Logistic-Remark", l_rmk)
                            st.success("Updated!"); time.sleep(1); st.rerun()