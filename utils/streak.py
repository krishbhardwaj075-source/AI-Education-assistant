from datetime import date
from Database.database import cursor, conn
def update_streak(user_id):
    today = date.today()
    cursor.execute("SELECT streak, last_study FROM users WHERE id=?", (user_id,))
    data = cursor.fetchone()
    current_streak = data[0] if data and data[0] else 0
    last_day = data[1]
    if last_day:
        last_day = date.fromisoformat(last_day)

        if (today - last_day).days == 1:
            current_streak += 1
        elif (today - last_day).days > 1:
            current_streak = 1
    else:
        current_streak = 1
    cursor.execute("""
    UPDATE users 
    SET streak=?, last_study=? 
    WHERE id=?
    """, (current_streak, today, user_id))
    conn.commit()
    return current_streak