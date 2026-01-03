import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. การตั้งค่าเบื้องต้น ---
DB_NAME = "po_database_v2.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # ปรับคอลัมน์แยก Product และ PO-Qty
    c.execute('''CREATE TABLE IF NOT EXISTS po_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT,
                  po_id TEXT,
                  customer TEXT,
                  product TEXT,
                  po_qty REAL,
                  part_no TEXT,
                  customer_eta_date TEXT,
                  date_issue_po TEXT,
                  sales_remark TEXT,
                  planning_production_date TEXT,
                  planning_remark TEXT,
                  logistic_ship_date TEXT,
                  logistic_remark TEXT,
                  config TEXT)''')
    conn.commit()
    conn.close()

# --- 2. ฟังก์ชันส่งอีเมล (เหมือนเดิม) ---
def send_email_alert(po_id, customer):
    try:
        sender_email = st.secrets["email"]["SENDER_EMAIL"]
        sender_password = st.secrets["email"]["SENDER_APP_PASSWORD"]
        receiver_emails = st.secrets["email"]["ALERT_RECEIVER"]
        msg = MIMEMultipart(); msg['From'] = sender_email; msg['To'] = ", ".join(receiver_emails)
        msg['Subject'] = f"🚨 New PO Alert: {po_id} - {customer}"
        body = f"มีการเพิ่มข้อมูล PO ใหม่ในระบบ\n\nPO ID: {po_id}\nCustomer: {customer}\nบันทึกเมื่อ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(sender_email, sender_password); server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"Cannot send email: {e}"); return False

# --- 3. หน้าจอหลัก ---
st.set_page_config(page_title="SIM PO Manager V2", layout="wide")
st.title("📦 ระบบจัดการ PO (Version 2.1 - แยก Product & Qty)")
init_db()

menu = ["📊 Dashboard", "➕ เพิ่มข้อมูล PO", "🛡️ Admin & Backup"]
choice = st.sidebar.selectbox("เมนูการใช้งาน", menu)

if choice == "📊 Dashboard":
    st.subheader("รายการ PO ทั้งหมด")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM po_records ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

elif choice == "➕ เพิ่มข้อมูล PO":
    st.subheader("กรอกข้อมูล PO (Product เป็น Dropdown)")
    with st.form("po_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            po_id = st.text_input("PO ID")
            customer = st.text_input("Customer")
            # --- ปรับเป็น Dropdown และแยกช่อง Qty ---
            product_list = ["Mold", "Mold Part", "Mold Services", "Mold Repair", "Mass-Part", "Steel Bush", "Other"]
            product = st.selectbox("Product", product_list)
            po_qty = st.number_input("PO-Qty", min_value=0.0, step=1.0)
            part_no = st.text_input("Part No")
        with col2:
            eta = st.date_input("Customer-ETA-Date")
            issue_date = st.date_input("Date-Issue-PO")
            p_date = st.date_input("Planning-Production-Date")
            l_date = st.date_input("Logistic-Ship-Date")
            config = st.text_input("Config")
        
        st.write("---")
        sales_rem = st.text_area("Sales-Remark")
        plan_rem = st.text_area("Planning-Remark")
        log_rem = st.text_area("Logistic-Remark")

        submitted = st.form_submit_button("บันทึกข้อมูลและส่งแจ้งเตือน")
        
        if submitted:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute('''INSERT INTO po_records 
                         (timestamp, po_id, customer, product, po_qty, part_no, customer_eta_date, 
                          date_issue_po, sales_remark, planning_production_date, planning_remark, 
                          logistic_ship_date, logistic_remark, config) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (timestamp, po_id, customer, product, po_qty, part_no, str(eta), 
                       str(issue_date), sales_rem, str(p_date), plan_rem, str(l_date), log_rem, config))
            conn.commit(); conn.close()
            with st.spinner('กำลังส่งอีเมลแจ้งเตือน...'):
                if send_email_alert(po_id, customer):
                    st.success(f"บันทึกข้อมูลเรียบร้อยและส่งอีเมลแจ้งเตือนแล้ว!")
                else:
                    st.warning("บันทึกข้อมูลแล้ว แต่ส่งเมลไม่สำเร็จ")

elif choice == "🛡️ Admin & Backup":
    st.subheader("ส่วนจัดการข้อมูล (Export Excel)")
    conn = sqlite3.connect(DB_NAME); df = pd.read_sql("SELECT * FROM po_records", conn); conn.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='PO_Backup')
    st.download_button(label="Download All Data as Excel", data=output.getvalue(),
                       file_name=f"PO_Backup_{datetime.now().strftime('%Y%m%d')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
