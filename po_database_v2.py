import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import smtplib
from email.message import EmailMessage
import time
import io

# ==================================================
# 1. INITIALIZE & DATABASE CONFIG
# ==================================================
DB_NAME = "po_master_2026.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # ตารางหลัก (อิงตามคอลัมน์เดิมที่คุณรุ่งมี)
    c.execute('''CREATE TABLE IF NOT EXISTS po_records
                 (Timestamp TEXT, [PO ID] TEXT PRIMARY KEY, Customer TEXT, 
                  Product TEXT, [PO-Qty] REAL, [Part No] TEXT, 
                  [Customer-ETA-Date] TEXT, [Date-Issue-PO] TEXT, [Sales-Remark] TEXT, 
                  [Planning-Production-Date] TEXT, [Planning-Remark] TEXT, 
                  [Logistic-Ship-Date] TEXT, [Logistic-Remark] TEXT, Config TEXT)''')
    
    # ตาราง Users (สร้างไว้ทดสอบ ถ้าไม่มีระบบ Login เดิม)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (Email TEXT PRIMARY KEY, Password TEXT, Name TEXT, Role TEXT)''')
    
    # เพิ่ม User ตัวอย่าง (เฉพาะครั้งแรก)
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sim.com', '1234', 'K.Rung', 'admin')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('fern@sim.com', '1234', 'Fern', 'admin')")
    
    conn.commit()
    conn.close()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

st.set_page_config(page_title="PO Master 2026 - Siam Intermold", layout="wide")
init_db()

# ดึงข้อมูลจาก Streamlit Secrets (สำหรับ Email)
SENDER_EMAIL = st.secrets["email"]["SENDER_EMAIL"]
SENDER_APP_PASSWORD = st.secrets["email"]["SENDER_APP_PASSWORD"]
ALERT_RECEIVER = st.secrets["email"]["ALERT_RECEIVER"]

# ==================================================
# 2. CORE FUNCTIONS (SQLITE VERSION)
# ==================================================
def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM po_records ORDER BY Timestamp DESC", conn)
    conn.close()
    return df

def update_po_record(po_id, col_name, val):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        query = f'UPDATE po_records SET "{col_name}" = ? WHERE "[PO ID]" = ?'
        c.execute(query, (str(val), str(po_id)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Update Error: {e}")
        return False

def send_full_alert(po_id, cust, eta, issue_date):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"📣 New PO Created - {po_id} [{cust}]"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECEIVER)
        html_content = f"<html><body style='font-family: Arial;'><h3>📣 New PO Registration</h3><p>PO: {po_id}<br>Customer: {cust}<br>ETA: {eta}</p></body></html>"
        msg.add_alternative(html_content, subtype='html')
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
        return True
    except: return False

# ==================================================
# 3. LOGIN INTERFACE
# ==================================================
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>Log In (Database Ver.)</h2>", unsafe_allow_html=True)
        em = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME)
            df_u = pd.read_sql(f"SELECT * FROM users WHERE Email='{em.strip()}' AND Password='{pw}'", conn)
            conn.close()
            if not df_u.empty:
                st.session_state.authenticated = True
                st.session_state.user_info = df_u.iloc[0].to_dict()
                st.rerun()
            else: st.error("Email หรือ Password ไม่ถูกต้อง")
    st.stop()

# ==================================================
# 4. MAIN CONTENT
# ==================================================
user = st.session_state.user_info
role = str(user.get('Role', '')).strip().lower()
u_name = str(user.get('Name', '')).strip()

with st.sidebar:
    st.info(f"👤 {u_name} ({role})")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    # --- ปุ่ม Backup สำหรับคุณ Fern ---
    st.divider()
    if st.button("📥 Download Excel Backup"):
        df_export = load_data()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("Click to Save", output.getvalue(), f"Backup_{date.today()}.xlsx")

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
            st.dataframe(df_all, use_container_width=True, hide_index=True)

        elif page_name == "➕ Create PO":
            st.header("➕ Create New PO")
            with st.form("f_create", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    p_id = st.text_input("PO ID *")
                    cst = st.text_input("Customer *")
                    product = st.selectbox("Product", ["Mold", "Mold Part", "Mold Services", "Mold Repair", "Mass-Part", "Steel Bush", "Other"])
                    qty = st.number_input("PO-Qty", min_value=0.0)
                with col2:
                    iss_date = st.date_input("Date Issue PO", date.today())
                    eta = st.date_input("Customer ETA", date.today())
                    part_no = st.text_input("Part No")
                
                remark = st.text_area("Sales Remark")
                
                if st.form_submit_button("Save"):
                    if p_id and cst:
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute('''INSERT INTO po_records 
                            (Timestamp, [PO ID], Customer, Product, [PO-Qty], [Part No], [Customer-ETA-Date], [Date-Issue-PO], [Sales-Remark], 
                             [Planning-Production-Date], [Planning-Remark], [Logistic-Ship-Date], [Logistic-Remark], Config)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (datetime.now().strftime("%Y-%m-%d %H:%M"), p_id, cst, product, qty, part_no, str(eta), str(iss_date), remark, "", "", "", "", ""))
                        conn.commit(); conn.close()
                        send_full_alert(p_id, cst, str(eta), str(iss_date))
                        st.success("Saved!"); time.sleep(1); st.rerun()

        elif page_name == "🏭 Planning":
            st.header("🏭 Planning Update")
            # กรองเฉพาะรายการที่ยังไม่ได้ใส่ Planning Date
            df_p = df_all[df_all['Planning-Production-Date'] == ""]
            if not df_p.empty:
                with st.form("p_up"):
                    target = st.selectbox("Select PO ID", df_p['PO ID'].tolist())
                    p_date = st.date_input("Production Date")
                    p_rem = st.text_area("Planning Remark")
                    if st.form_submit_button("Update Planning"):
                        update_po_record(target, "Planning-Production-Date", str(p_date))
                        update_po_record(target, "Planning-Remark", p_rem)
                        st.success("Updated!"); time.sleep(1); st.rerun()
            else: st.write("ไม่มีรายการค้าง")

        elif page_name == "🚚 Logistic":
            st.header("🚚 Logistic Update")
            df_l = df_all[df_all['Logistic-Ship-Date'] == ""]
            if not df_l.empty:
                with st.form("l_up"):
                    target = st.selectbox("Select PO ID", df_l['PO ID'].tolist())
                    s_date = st.date_input("Ship Date")
                    l_rem = st.text_area("Logistic Remark")
                    if st.form_submit_button("Update Logistic"):
                        update_po_record(target, "Logistic-Ship-Date", str(s_date))
                        update_po_record(target, "Logistic-Remark", l_rem)
                        st.success("Updated!"); time.sleep(1); st.rerun()
            else: st.write("ไม่มีรายการค้าง")
