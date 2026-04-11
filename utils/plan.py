def generate_plan(subjects, days_left, study_hours, preferred_session="balanced", max_subjects_per_day=4, consistency_score=None):
    plan = []
    if not subjects:
        return plan

    difficulty_rank = {"easy": 1, "medium": 2, "hard": 3}

    for subject in subjects:
        difficulty = subject["difficulty"].lower()
        topics = subject["topics"]
        days_left = subject["days_left"]
        latest_status = subject.get("latest_status")
        avg_progress = subject.get("avg_progress")
        is_weak = subject.get("is_weak", False)
        is_recommended = subject.get("is_recommended", False)

        if difficulty == "easy":
            diff_weigth = 1
        elif difficulty == "medium":
            diff_weigth = 2
        elif difficulty == "hard":
            diff_weigth = 3
        else:
            diff_weigth = 1

        if latest_status == 0:
            latest_priority = 3
        elif latest_status == 50:
            latest_priority = 2
        elif latest_status == 100:
            latest_priority = 0
        else:
            latest_priority = 2

        if avg_progress is None:
            avg_priority = 2
        elif avg_progress <= 30:
            avg_priority = 3
        elif avg_progress <= 60:
            avg_priority = 2
        elif avg_progress <= 80:
            avg_priority = 1
        else:
            avg_priority = 0

        topic_factor = {
            "easy": 1.0,
            "medium": 1.15,
            "hard": 1.35
        }.get(difficulty, 1.0)

        priority_score = diff_weigth + latest_priority + avg_priority
        if is_weak:
            priority_score += 2
        if is_recommended:
            priority_score += 2

        if days_left <= 3:
            priority_score += 2
        elif days_left <= 7:
            priority_score += 1

        effective_topics = topics * topic_factor
        subject["weight"] = priority_score * effective_topics / max(days_left, 1)
        subject["difficulty_rank"] = difficulty_rank.get(difficulty, 1)

    subjects.sort(key=lambda item: item["weight"], reverse=True)

    if consistency_score is not None and consistency_score < 50:
        allowed_subjects = min(max_subjects_per_day, 3)
        min_hours = 1.0
    elif consistency_score is not None and consistency_score < 80:
        allowed_subjects = min(max_subjects_per_day, 4)
        min_hours = 0.75
    else:
        allowed_subjects = max_subjects_per_day
        min_hours = 0.5

    allowed_subjects = max(1, allowed_subjects)
    selected_subjects = subjects[:allowed_subjects]
    total_weigth = sum(subject["weight"] for subject in selected_subjects)
    if total_weigth <= 0:
        total_weigth = len(selected_subjects)

    daily_plan = []
    for subject in selected_subjects:
        hours = round((subject["weight"] / total_weigth) * study_hours, 1)
        if study_hours >= min_hours * len(selected_subjects) and hours < min_hours:
            hours = min_hours
        daily_plan.append({
            "name": subject["name"],
            "hours": hours,
            "difficulty_rank": subject["difficulty_rank"],
            "days_left": subject["days_left"]
        })

    if preferred_session == "morning":
        daily_plan.sort(key=lambda item: (-item["difficulty_rank"], -item["hours"], item["days_left"]))
    elif preferred_session == "night":
        daily_plan.sort(key=lambda item: (item["difficulty_rank"], -item["hours"], item["days_left"]))
    else:
        daily_plan.sort(key=lambda item: (-item["hours"], item["days_left"], -item["difficulty_rank"]))

    for task in daily_plan:
        task.pop("difficulty_rank", None)
        task.pop("days_left", None)

    plan.append({
        "day": 1,
        "subjects": daily_plan
    })
    return plan
