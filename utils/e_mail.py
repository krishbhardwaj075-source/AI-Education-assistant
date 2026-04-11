import smtplib
from email.mime.text import MIMEText
def send_otp(email,otp):
    sender="krishbhardwaj.075@gmail.com"
    password="xgjo ueqc avlx qqgp"
    message=MIMEText(f"Your OTP for verification: {otp}")
    message["subject"]="AI Study Planner OTP"
    message["From"]=sender
    message["To"]=email
    server=smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(sender,password)
    server.sendmail(sender,email,message.as_string())
    server.quit()