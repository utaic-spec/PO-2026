import smtplib
from email.message import EmailMessage

# ==================================================
# EMAIL CONFIG
# ==================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT_SSL = 465

SENDER_EMAIL = "siamintermoldpoalert@gmail.com"
SENDER_APP_PASSWORD = "dycmrqdwjclyveic"

ALERT_RECEIVER = [
    "utai.c@siamintermold.com"
    # เพิ่ม planning / logistic ได้ทีหลัง
]

# ==================================================
# SEND PO ALERT EMAIL
# ==================================================
def send_po_email(po: dict):
    msg = EmailMessage()

    msg["Subject"] = f"📦 New PO Created: {po.get('PO ID', '-')}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(ALERT_RECEIVER)

    body = f"""
📦 New PO Created

PO ID            : {po.get('PO ID', '-')}
Customer         : {po.get('Customer', '-')}
Product          : {po.get('Product', '-')}
Quantity         : {po.get('PO-Qty', '-')}
Customer ETA     : {po.get('Customer-ETA-Date', '-')}
Date Issue PO    : {po.get('Date-Issue-PO', '-')}

📝 Sales Remark
{po.get('Sales-Remark', '-')}

👉 Planning & Logistic Update Link
{po.get('APP_URL', '(URL not configured yet)')}

--------------------------------------------------
This is an automated notification.
Please do not reply.
"""
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        smtp.send_message(msg)
