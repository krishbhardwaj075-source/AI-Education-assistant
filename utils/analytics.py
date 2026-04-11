def get_performance_data(cursor, user_id):
    cursor.execute("""
    SELECT date, status 
    FROM progress 
    WHERE user_id=?
    ORDER BY date ASC
    """, (user_id,))

    data = cursor.fetchall()

    dates = []
    scores = []
    for row in data:
        dates.append(row[0])
        scores.append(row[1])
    return dates, scores