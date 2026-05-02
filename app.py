import sqlite3
from flask import  Flask,render_template,request,redirect,session,flash
import random
import time
import os
from datetime import datetime
from utils.analytics import get_performance_data
from sklearn.preprocessing import PolynomialFeatures
import pickle
from utils.e_mail import send_otp
from utils.streak import update_streak
from utils.plan import generate_plan
from utils.chatbot import get_ai_response
from utils.recommendation import build_priority_recommendation
from Database.database import cursor,conn
poly=PolynomialFeatures(degree=2, include_bias=False)
app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY")
rf_model=pickle.load(open("Model/study_rf_model.pkl","rb"))
scaler=pickle.load(open("Model/scaler.pkl","rb"))
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form["name"]
        email=request.form["email"]
        password=request.form["password"]
        username=request.form["username"]
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user_exist=cursor.fetchone()
        if user_exist:
            return "User Already Exists!"
        else:
            otp=random.randint(100000,999999)
            session["otp"]=otp
            session["otp_time"]=time.time()
            session["email"]=email
            send_otp(email,otp)
            session["temp"]={
                "name":name,
                "username":username,
                "email":email,
                "password":password
            }
            return redirect("/verify")
    return render_template("signup.html")

@app.route("/verify", methods=["GET","POST"])
def verify():
    if request.method=="POST":
        user_otp=request.form["otp"]
        if time.time() -session["otp_time"]>90:
            return "OTP Expired! Please request a new otp"
        if int(user_otp)==session["otp"]:
            cursor.execute(
                "INSERT INTO users(name,username,email,password) VALUES(?,?,?,?)",
                (
                session["temp"]["name"],
                session["temp"]["username"],
                session["temp"]["email"],
                session["temp"]["password"]
                )
                )
            conn.commit()
            flash("OTP verified successfully! Please login.")
            return redirect("/login")
        else:
            return "Invalid OTP"
    return render_template("verify.html")

@app.route("/resend-otp")
def resend_otp():
    if "email" not in session:
        return redirect("/signup")
    otp = random.randint(100000,999999)
    session["otp"] = otp
    session["otp_time"] = time.time()
    send_otp(session["email"], otp)
    flash("New OTP sent to your email!")
    return redirect("/verify")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        identity=request.form["identity"]#E-mail
        password=request.form["password"]
        cursor.execute(
            "SELECT * FROM users WHERE (username=? OR email=?) AND password=?",
            (identity,identity,password)
        )
        user=cursor.fetchone()
        if user:
            session["user_id"]=user[0]
            session["user"]=user[1]
            return redirect("/dashboard")
        return "Invalid Email or Password!"
    return render_template("login.html")
        
@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        user_id=session["user_id"]
        study_hours = session.get("study_hours", 4)
        cursor.execute("SELECT COUNT(*) FROM subjects WHERE user_id=? AND (status IS NULL OR status != 'completed')",(user_id,))
        total_subjects=cursor.fetchone()[0]
        cursor.execute("""
        SELECT subject_name FROM subjects 
        WHERE user_id=? AND difficulty='Hard' LIMIT 1
        """, (user_id,))
        weak=cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM subjects WHERE user_id=? AND STATUS='completed'", (user_id,))
        completed=cursor.fetchone()[0]
        weak_sub=weak[0] if weak else "none"
        labels=[]
        values=[]
        cursor.execute("""
        SELECT difficulty, COUNT(*) 
        FROM subjects 
        WHERE user_id=? 
        GROUP BY difficulty
        """, (user_id,))
        data = cursor.fetchall()
        labels = [ row[0] for row in data]
        values = [ row[1] for row in data]

        hours=round(study_hours,1)
        cursor.execute("""
        SELECT subject_name, difficulty, topics, exam_date
        FROM subjects
        WHERE user_id=? AND (status IS NULL OR status != 'completed')
        """, (user_id,))
        subject_details = cursor.fetchall()
        
        cursor.execute("SELECT subject_name FROM subjects WHERE user_id=? AND status!='completed' ORDER BY subject_name ASC", (user_id,))
        subject_list = [row[0] for row in cursor.fetchall()]

        
        cursor.execute("""
        SELECT subject_name, MAX(id),day, status
        FROM progress
        WHERE user_id=?
        GROUP BY subject_name
        ORDER BY MAX(id) DESC
        """, (user_id,))
        progress_data = cursor.fetchall()

        cursor.execute("""SELECT streak FROM users WHERE id=?""", (user_id,))
        row = cursor.fetchone()
        streak=row[0] if row and row[0] else 0
        if progress_data:
            avg = round(sum([row[3] for row in progress_data]) / len(progress_data), 2)
        else:
            avg = 0
        if avg < 50:
            insight = "⚠️ You are not consistent. Follow your plan daily."
        elif avg < 80:
            insight = "👍 Good, but you can improve consistency."
        else:
            insight = "🚀 Excellent consistency! Keep it up."

        latest_subject_status = {}
        for row in progress_data:
            subject_name = row[0]
            status = row[3]
            latest_subject_status[subject_name] = status

        progress_summary = {}
        for _, _, subject_name, status in progress_data:
            if subject_name not in progress_summary:
                progress_summary[subject_name] = {
                    "latest_status": status,
                    "statuses": []
                }
            progress_summary[subject_name]["statuses"].append(status)

        for subject_name, summary in progress_summary.items():
            statuses = summary["statuses"]
            summary["avg_progress"] = round(sum(statuses) / len(statuses), 2) if statuses else None

        completed_subjects = []
        partial_subjects = []
        not_done_subjects = []

        for subject_name in subject_list:
            status = latest_subject_status.get(subject_name, 0)
            if status == 100:
                completed_subjects.append(subject_name)
            elif status == 50:
                partial_subjects.append(subject_name)
            else:
                not_done_subjects.append(subject_name)

        completed = len(completed_subjects)
        partial_count = len(partial_subjects)
        not_done_count = len(not_done_subjects)
        reminders=[]
        if not_done_count>0:
            reminders.append(f"You have {not_done_count} pending tasks ⚠️")
        if weak_sub!="none":
            reminders.append(f"Consider focusing on {weak_sub} which is marked as hard! 💪")
        if streak == 0:
            reminders.append("You don't have an active streak. Try to study daily to build a streak! 🔥")
        recommendation = build_priority_recommendation(subject_details)
        return render_template("dashboard.html", name=session["user"],subjects=total_subjects,weak_sub=weak_sub,recommendation=recommendation,completed_subjects=completed_subjects,partial_subjects=partial_subjects,not_done_subjects=not_done_subjects,labels=labels,values=values,study_hours=hours,completed=completed,partial_count=partial_count,not_done_count=not_done_count,subject_list=subject_list, data=progress_data,streak=streak, avg=avg,reminders=reminders, insight=insight,day=1)
    return redirect("/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/add-subject", methods=["GET","POST"])
def add_sub():
    if "user" not in session:
        return redirect("/login")
    if request.method=="POST":
        subject=request.form["subject"]
        difficulty=request.form["difficulty"]
        topics=request.form["topics"]
        exam_date=request.form["exam_date"]

        user_id=session.get("user_id")
        cursor.execute(
            "INSERT INTO subjects(user_id,subject_name,difficulty,topics,exam_date) VALUES(?,?,?,?,?)",
            (user_id,subject,difficulty,topics,exam_date)
        )
        conn.commit()
        return redirect("/subjects")
    return render_template("add_sub.html")

@app.route("/subjects")
def subjects():
    if "user" not in session:
        return redirect("/login")
    cursor.execute("SELECT id, subject_name, difficulty, topics, exam_date, status FROM subjects WHERE user_id=? AND (status IS NULL OR status != 'completed') ORDER BY exam_date ASC, subject_name ASC",(session["user_id"],))
    data=cursor.fetchall()

    return render_template("subject.html",subjects=data)

@app.route("/delete-subject/<int:id>")
def delete(id):
    cursor.execute("DELETE FROM subjects WHERE id=? AND user_id=?",(id, session["user_id"]))
    conn.commit()
    return redirect("/subjects")

@app.route("/study_planner",methods=["GET","POST"])
def study_plan():
    if "user_id" not in session:
        return redirect("/login")
    user_id=session["user_id"]
    plan=[]
    prediction=None
    recommendation=None
    new_plan=[]
    revision_tasks=[]
    planner_priority=None
    consistency_score=None
    preferred_session="balanced"
    max_subjects_per_day=4
    cursor.execute("""
    SELECT id, subject_name, status
    FROM progress
    WHERE user_id=?
    ORDER BY id DESC
    """, (user_id,))
    planner_progress = cursor.fetchall()
    cursor.execute("""SELECT subject_name,date FROM progress
WHERE user_id=? AND status=100 ORDER BY date DESC""", (user_id,))
    completed_progress = cursor.fetchall()
    for subject,data in completed_progress:
        try:
            last_date=datetime.strptime(data, "%Y-%m-%d")
            if(datetime.now()-last_date).days>=3:
                revision_tasks.append({
                    "subject": subject,
                    "type": "Revision",
                    "priority": "High"
                })
        except:
            pass
    progress_summary = {}
    for _, subject_name, status in planner_progress:
        if subject_name not in progress_summary:
            progress_summary[subject_name] = {
                "latest_status": status,
                "statuses": []
            }
        progress_summary[subject_name]["statuses"].append(status)

    for subject_name, summary in progress_summary.items():
        statuses = summary["statuses"]
        summary["avg_progress"] = round(sum(statuses) / len(statuses), 2) if statuses else None

    cursor.execute("""
    SELECT subject_name FROM subjects
    WHERE user_id=? AND difficulty='Hard'
    ORDER BY exam_date ASC, subject_name ASC
    LIMIT 1
    """, (user_id,))
    weak = cursor.fetchone()
    weak_sub = weak[0] if weak else None

    cursor.execute("""
    SELECT status FROM progress
    WHERE user_id=? AND date >= DATE('now', '-7 day')
    """, (user_id,))
    recent_progress = [row[0] for row in cursor.fetchall()]
    if recent_progress:
        consistency_score = round(sum(recent_progress) / len(recent_progress), 2)
    if request.method=="POST":
        
        study=float(request.form.get("study"))
        attendance=float(request.form.get("attendance"))
        participation=float(request.form.get("participation"))
        preferred_session=request.form.get("preferred_session", "balanced")
        max_subjects_per_day=int(request.form.get("max_subjects_per_day", 4))

        study_eff=study*participation
        attendance_ratio=attendance/100

        from sklearn.preprocessing import PolynomialFeatures
        features=[[study,attendance,participation,study_eff]]
        poly=PolynomialFeatures(degree=2, include_bias=False)
        features_poly=poly.fit_transform(features)
        features_scaled=scaler.transform(features_poly)
        result=rf_model.predict(features_scaled)
        days_left=int(request.form.get("days_left", 30))
        
        prediction=round(result[0],2)
        if prediction >= 85:
            recommendation = "🚀 Excellent! Focus on revision."
        elif prediction >= 70:
            recommendation = "👍 Good, but improve weak areas."
        else:
            recommendation = "⚠️ Increase study time & revise basics."
        cursor.execute(""" SELECT subject_name,difficulty,topics,exam_date FROM subjects WHERE user_id=? AND (status IS NULL OR status != 'completed') ORDER BY exam_date ASC, subject_name ASC """, (user_id,))
        data=cursor.fetchall()
        planner_priority = build_priority_recommendation(data)
        from datetime import datetime
        subject_data=[]
        for subject in data:
            name=subject[0]
            difficulty=subject[1]
            topics=len(subject[2].split(",")) if subject[2] else 1
            try:
                if not subject[3]:
                    continue
                exam_date=datetime.strptime(subject[3], "%Y-%m-%d")
            except ValueError:
                continue
            today=datetime.today()
            days_left=(exam_date-today).days
            if days_left<=0:
                days_left=1
            summary = progress_summary.get(name, {})
            if summary.get("latest_status") == 100:
                continue
            subject_data.append({
                "name": name,
                "difficulty": difficulty,
                "topics": topics,
                "days_left": days_left,
                "latest_status": summary.get("latest_status"),
                "avg_progress": summary.get("avg_progress"),
                "is_weak": name == weak_sub,
                "is_recommended": planner_priority is not None and name == planner_priority["subject_name"]
            })
        total_days=int(request.form.get("days_left", 30))
        new_plan=generate_plan(subject_data,total_days, study, preferred_session=preferred_session, max_subjects_per_day=max_subjects_per_day, consistency_score=consistency_score)
        if new_plan:
            new_plan[0]["subjects"].extend(revision_tasks)
            session["study_hours"] = sum(task.get("hours", 1) for task in new_plan[0]["subjects"])
    return render_template("planner.html",plan=new_plan,prediction=prediction,recommendation=recommendation,planner_priority=planner_priority,consistency_score=consistency_score,preferred_session=preferred_session,max_subjects_per_day=max_subjects_per_day)

@app.route("/complete/<int:id>")
def complete(id):
    cursor.execute("UPDATE subjects SET status='completed' WHERE id=? AND user_id=?",(id, session["user_id"]))
    conn.commit()
    return redirect("/subjects")

@app.route("/chatbot", methods=["GET","POST"])
def bot():
    response=""
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    cursor.execute("""
    SELECT subject_name, difficulty, topics, exam_date
    FROM subjects
    WHERE user_id=? AND (status IS NULL OR status != 'completed')
    ORDER BY exam_date ASC, subject_name ASC
    """, (user_id,))
    subject_rows = cursor.fetchall()

    cursor.execute("""
    SELECT id, subject_name, status
    FROM progress
    WHERE user_id=?
    ORDER BY id DESC
    """, (user_id,))
    progress_rows = cursor.fetchall()

    latest_status_map = {}
    for _, subject_name, status in progress_rows:
        if subject_name not in latest_status_map:
            latest_status_map[subject_name] = status

    cursor.execute("""
    SELECT subject_name FROM subjects
    WHERE user_id=? AND difficulty='Hard'
    ORDER BY exam_date ASC, subject_name ASC
    LIMIT 1
    """, (user_id,))
    weak = cursor.fetchone()
    weak_sub = weak[0] if weak else None

    priority_pick = build_priority_recommendation(subject_rows)
    chatbot_context = {
        "subjects": [row[0] for row in subject_rows],
        "latest_status_map": latest_status_map,
        "weak_subject": weak_sub,
        "priority_subject": priority_pick["subject_name"] if priority_pick else None,
        "study_hours": session.get("study_hours")
    }

    if request.method=="POST":
        user_input=request.form.get("message")
        response=get_ai_response(user_input, chatbot_context)
    return render_template("chatbot.html",response=response)

@app.route('/track', methods=['POST'])
def track():
    user_id = session['user_id']
    day = request.form['day']
    subject = request.form['subject']
    status = int(request.form['status'])

    cursor.execute("""SELECT id FROM progress WHERE user_id=? AND subject_name=? AND day=?""",(user_id, subject, day))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
                       UPDATE progress SET status=?, date=DATE('now')
                       WHERE id=?
                       """, (status, existing[0]))
    else:
        cursor.execute("""
                       INSERT INTO progress (user_id, day, subject_name, status, date)
                       VALUES (?, ?, ?, ?, DATE('now'))
                       """, (user_id, day, subject, status))
    if status == 100:
        cursor.execute("""
        UPDATE subjects SET status='completed' 
        WHERE user_id=? AND subject_name=?
        """, (user_id, subject))
        update_streak(user_id)
    conn.commit()

    return redirect('/dashboard')

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    name=session.get("user", "Student")
    dates, scores = get_performance_data(cursor, user_id)
    cursor.execute("""
    SELECT subject_name, AVG(status)
    FROM progress
    WHERE user_id=?
    GROUP BY subject_name
    """, (user_id,))
    subject_perf = cursor.fetchall() or []
    consistency = round(sum(scores)/len(scores), 2) if scores else 0
    weak_subjects = [sub for sub, score in subject_perf if score is not None and score < 50]
    if len(scores) > 1:
        trend = "up" if scores[-1] > scores[0] else "down"
    else:
        trend = "neutral"
    cursor.execute("""
    SELECT date, status FROM progress
    WHERE user_id=?
    """, (user_id,))
    heatmap = cursor.fetchall() or []
    cursor.execute("""
    SELECT COUNT(*) FROM subjects 
    WHERE user_id=? AND status='completed'
    """, (user_id,))
    completed = cursor.fetchone()[0] or 0
    cursor.execute("""
    SELECT subject_name, MAX(id), status 
    FROM progress 
    WHERE user_id=? 
    GROUP BY subject_name
    """, (user_id,))
    latest_status = cursor.fetchall()
    partial = sum(1 for row in latest_status if row[2] == 50)
    not_done = sum(1 for row in latest_status if row[2] == 0)
    if consistency < 50:
        insight = "You are inconsistent 😬"
    elif consistency < 80:
        insight = "You are improving 👍"
    else:
        insight = "Excellent performance 🚀"
    return render_template("analytics.html",
        dates=dates,
        scores=scores,
        name=name,
        subject_perf=subject_perf,
        consistency=consistency,
        weak_subjects=weak_subjects,
        trend=trend,
        heatmap=heatmap,
        insight=insight,
        completed=completed,
        partial=partial,
        not_done=not_done
    )
@app.route("/revision")
def revision():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    cursor.execute("""
    SELECT subject_name, date
    FROM progress
    WHERE user_id=? AND status=100
    """, (user_id,))
    data = cursor.fetchall()
    from datetime import datetime
    revision_list = []
    for subject, date in data:
        try:
            last_date = datetime.strptime(date, "%Y-%m-%d")
            if (datetime.now() - last_date).days >= 2:
                revision_list.append(subject)
        except:
            pass
    return render_template("revision.html", revision_list=revision_list)
if __name__=="__main__":
    app.run(debug=True)