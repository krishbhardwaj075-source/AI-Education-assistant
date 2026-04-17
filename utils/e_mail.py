import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()
def send_otp(email,otp):
    try:
        sender=os.getenv("EMAIL_SENDER")
        password=os.getenv("EMAIL_PASSWORD")
        message=MIMEText(f"Your OTP for verification: {otp}")
        message["subject"]="AI Study Planner OTP"
        message["From"]=sender
        message["To"]=email
        server=smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login(sender,password)
        server.sendmail(sender,email,message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False