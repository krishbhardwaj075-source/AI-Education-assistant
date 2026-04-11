from datetime import datetime


def build_priority_recommendation(subject_details):
    difficulty_rank = {"Hard": 3, "Medium": 2, "Easy": 1}
    today = datetime.today().date()
    strict_candidates = []
    fallback_candidates = []

    for subject_name, difficulty, topics, exam_date in subject_details:
        topic_count = len([topic.strip() for topic in (topics or "").split(",") if topic.strip()])

        if not exam_date:
            continue

        try:
            exam_day = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_left = (exam_day - today).days
        if days_left < 0:
            continue

        candidate = {
            "subject_name": subject_name,
            "difficulty": difficulty,
            "topic_count": topic_count,
            "days_left": days_left,
        }

        if days_left <= 30:
            fallback_candidates.append(candidate)

        if topic_count >= 5 and days_left <= 14:
            strict_candidates.append(candidate)

    candidates = strict_candidates or fallback_candidates

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item["days_left"],
            -item["topic_count"],
            -difficulty_rank.get(item["difficulty"], 0),
            item["subject_name"].lower(),
        )
    )

    top_pick = candidates[0]
    return {
        "subject_name": top_pick["subject_name"],
        "topic_count": top_pick["topic_count"],
        "days_left": top_pick["days_left"],
        "difficulty": top_pick["difficulty"],
        "message": f"Start with {top_pick['subject_name']}. It has {top_pick['topic_count']} topics and the exam is in {top_pick['days_left']} days.",
    }
