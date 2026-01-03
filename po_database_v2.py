import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- การตั้งค่าเบื้องต้น ---
DB_NAME = "po_database.db"

def init_db():
    """สร้างตารางข้อมูลถ้ายังไม่มี"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS po_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  po_number TEXT, 
                  item_name TEXT, 
                  amount REAL, 
                  date_added TEXT, 
                  added_by TEXT)''')
    conn.commit()
    conn.close()

def save_data(po_num, item, amt, user):
    """บันทึกข้อมูลลง Database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO po_records (po_number, item_name, amount, date_added, added_by) VALUES (?, ?, ?, ?, ?)",
              (po_num, item, amt, now, user))
    conn.commit()
    conn.close()

def load_data():
    """ดึงข้อมูลทั้งหมดออกมาเป็น DataFrame"""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM po_records ORDER BY id DESC", conn)
    conn.close()
    return df

# --- หน้าจอหลัก ---
st.title("📦 ระบบจัดการ PO (Version 2 - Database)")
init_db()

# ส่วน Login ง่ายๆ (ปรับตามที่คุณรุ่งต้องการ)
user = st.sidebar.text_input("Username", value="Fern")

menu = ["Dashboard", "เพิ่มข้อมูล PO", "Admin & Backup"]
choice = st.sidebar.selectbox("เมนูการใช้งาน", menu)

if choice == "Dashboard":
    st.subheader("📊 รายการ PO ทั้งหมดในระบบ")
    df = load_data()
    st.dataframe(df, use_container_width=True)

elif choice == "เพิ่มข้อมูล PO":
    st.subheader("➕ บันทึก PO ใหม่")
    with st.form("po_form"):
        po_num = st.text_input("เลขที่ PO")
        item = st.text_input("ชื่อสินค้า")
        amt = st.number_input("จำนวนเงิน", min_value=0.0)
        submitted = st.form_submit_button("บันทึกข้อมูล")
        
        if submitted:
            save_data(po_num, item, amt, user)
            st.success(f"บันทึก PO {po_num} เรียบร้อยแล้ว!")

elif choice == "Admin & Backup":
    st.subheader("🛡️ ส่วนจัดการข้อมูล (สำหรับคุณ Fern)")
    df = load_data()
    
    # --- ส่วน Export ข้อมูลเป็น Excel ---
    st.write("### 📥 สำรองข้อมูล (Backup)")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='PO_Backup')
    
    st.download_button(
        label="Download All Data as Excel",
        data=output.getvalue(),
        file_name=f"PO_Backup_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    st.warning("คำแนะนำ: ควรดาวน์โหลดไฟล์ Backup เก็บไว้ทุกสัปดาห์ครับ")