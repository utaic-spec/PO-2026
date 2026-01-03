import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import smtplib
from email.message import EmailMessage
import time

# ==================================================
# 1. INITIALIZE & CONFIG
# ==================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

st.set_page_config(page_title="PO Master 2026 - Siam Intermold", layout="wide")

SPREADSHEET_ID = "1dHa3wGMvEgZdkKiE8T2J9nzQmfoDTF3AnLWah-RcTWU"
SHEET_NAME = "PO2026"

# ดึงข้อมูลจาก Streamlit Secrets
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
            
            # ดึงข้อมูลจาก Secrets แบบ Dict
            creds_dict = {
                "type": st.secrets["gcp_service_account"]["type"],
                "project_id": st.secrets["gcp_service_account"]["project_id"],
                "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'), # แก้ปัญหาเรื่องขึ้นบรรทัดใหม่
                "client_email": st.secrets["gcp_service_account"]["client_email"],
                "client_id": st.secrets["gcp_service_account"]["client_id"],
                "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
            }
            
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
        except Exception as e:
            if i == retries - 1:
                st.error(f"⚠️ Connection Error: {e}")
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
    except:
        return False

def send_full_alert(po_id=None, cust=None, product_type=None, part_no=None, qty=None, eta=None, issue_date=None, remark=None):
    # แก้ไข URL หลังจาก Deploy สำเร็จแล้วมาแก้ที่นี่
    APP_URL = "https://your-app-name.streamlit.app" 
    try:
        msg = EmailMessage()
        msg['Subject'] = f"📣 New PO Created - {po_id} [{cust}]"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECEIVER)
        html_content = f"<html><body style='font-family: Arial;'><h3>📣 New PO Registration</h3><p>PO: {po_id}<br>Customer: {cust}<br>ETA: {eta}</p><a href='{APP_URL}'>Open System</a></body></html>"
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
        msg['Subject'] = f"⚠️ REMINDER: Pending PO (>24 Hours)"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECEIVER)
        rows = "".join([f"<tr><td>{i['PO ID']}</td><td>{i['Customer']}</td><td>{i['Entry Time']}</td></tr>" for i in items])
        html = f"<html><body><h3>รายการค้างเกิน 24 ชม.</h3><table border='1'><tr><th>PO</th><th>Customer</th><th>Time</th></tr>{rows}</table></body></html>"
        msg.add_alternative(html, subtype='html')
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
        pending = []
        for _, row in df_all.iterrows():
            ts = str(row.get('Timestamp', '')).strip()
            if ts:
                try:
                    ts_dt = pd.to_datetime(ts)
                    if (now - ts_dt).total_seconds()/3600 >= 24 and (not row.get('Planning-Production-Date') or not row.get('Logistic-Ship-Date')):
                        pending.append({"PO ID": row['PO ID'], "Customer": row['Customer'], "Entry Time": ts})
                except: continue
        if pending: return send_reminder_email(pending)
    except: return False

def should_send_today():
    try:
        ss = get_ss_with_retry()
        try: ws = ss.worksheet("Config")
        except: 
            ws = ss.add_worksheet(title="Config", rows="1", cols="2")
            ws.update_cell(1, 1, "Last-Reminder-Date")
        last_date = ws.cell(1, 2).value
        today = str(date.today())
        if last_date != today:
            ws.update_cell(1, 2, today)
            return True
        return False
    except: return False

# ==================================================
# 3. LOGIN INTERFACE
# ==================================================
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try: st.image('SIM-LOGO.jpg', width=658)
        except: st.warning("Logo not found.")
        with st.container(border=True):
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
    st.stop()

# ==================================================
# 4. MAIN CONTENT
# ==================================================
if st.session_state.authenticated:
    if 'reminder_checked' not in st.session_state:
        if should_send_today():
            with st.spinner("Checking Reminders..."):
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
            if page_name == "📊 View Database":
                st.header("📊 Purchase Order Database")
                if not df_all.empty:
                    st.dataframe(df_all, use_container_width=True, hide_index=True)
            
            elif page_name == "➕ Create PO":
                st.header("➕ Create New PO")
                with st.form("f_create", clear_on_submit=True):
                    p_id = st.text_input("PO ID *")
                    cst = st.text_input("Customer *")
                    iss_date = st.date_input("Date Issue PO", date.today())
                    eta = st.date_input("Customer ETA", date.today())
                    if st.form_submit_button("Save"):
                        if p_id and cst:
                            ws = get_ss_with_retry().worksheet(SHEET_NAME)
                            ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), p_id, cst, "", "", "", str(eta), str(iss_date), ""], value_input_option='USER_ENTERED')
                            send_full_alert(po_id=p_id, cust=cst, eta=str(eta), issue_date=str(iss_date))
                            st.success("Saved!"); time.sleep(1); st.rerun()

            elif page_name == "🏭 Planning":
                st.header("🏭 Planning Update")
                df_p = df_all[df_all['Planning-Production-Date'] == ""]
                st.dataframe(df_p, use_container_width=True)
                if not df_p.empty:
                    with st.form("p_up"):
                        target = st.selectbox("Select PO ID", df_p['PO ID'].tolist())
                        p_date = st.date_input("Production Date")
                        if st.form_submit_button("Update"):
                            update_po_record(target, "Planning-Production-Date", str(p_date))
                            st.success("Updated!"); time.sleep(1); st.rerun()

            elif page_name == "🚚 Logistic":
                st.header("🚚 Logistic Update")
                df_l = df_all[df_all['Logistic-Ship-Date'] == ""]
                st.dataframe(df_l, use_container_width=True)
                if not df_l.empty:
                    with st.form("l_up"):
                        target = st.selectbox("Select PO ID", df_l['PO ID'].tolist())
                        s_date = st.date_input("Ship Date")
                        if st.form_submit_button("Update"):
                            update_po_record(target, "Logistic-Ship-Date", str(s_date))
                            st.success("Updated!"); time.sleep(1); st.rerun()
