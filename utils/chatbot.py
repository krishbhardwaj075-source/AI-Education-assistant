import re
SUBJECT_KEYWORDS = [
    "dbms",
    "python",
    "dsa",
    "machine learning",
    "digital electronics",
    "operating system",
    "os",
    "computer fundamental",
    "generative ai",
    "ai",
    "asp.net",
    "dtp",
]
def _extract_number(pattern, text):
    match = re.search(pattern, text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _extract_subjects(text):
    found = []
    for subject in SUBJECT_KEYWORDS:
        if subject in text and subject not in found:
            found.append(subject)
    return found


def _format_subject(subject):
    mapping = {
        "dbms": "DBMS",
        "python": "Python",
        "dsa": "DSA",
        "machine learning": "Machine Learning",
        "digital electronics": "Digital Electronics",
        "operating system": "Operating System",
        "os": "Operating System",
        "computer fundamental": "Computer Fundamental",
        "generative ai": "Generative AI",
        "ai": "AI",
        "asp.net": "ASP.NET",
        "dtp": "DTP",
    }
    return mapping.get(subject, subject.title())


def _context_subjects(context):
    return context.get("subjects", []) if context else []


def _context_priority_subject(context):
    if context and context.get("priority_subject"):
        return context["priority_subject"]
    subjects = _context_subjects(context)
    return subjects[0] if subjects else None


def _context_weak_subject(context):
    if context:
        return context.get("weak_subject")
    return None


def _context_latest_status(context, subject_name):
    if not context:
        return None
    return context.get("latest_status_map", {}).get(subject_name)


def _status_label(status):
    if status == 100:
        return "completed"
    if status == 50:
        return "partial"
    if status == 0:
        return "not done"
    return "not tracked"


def _build_plan_response(message, lower_message, context):
    study_hours = _extract_number(r"(\d+)\s*(?:hours|hrs|hour|hr)", lower_message)
    if study_hours is None and context and context.get("study_hours"):
        study_hours = context["study_hours"]
    exam_days = _extract_number(r"(\d+)\s*(?:days|day)", lower_message)
    detected_subjects = [_format_subject(subject) for subject in _extract_subjects(lower_message)]
    if not detected_subjects:
        detected_subjects = _context_subjects(context)[:3]

    priority_subject = _context_priority_subject(context)
    weak_subject = _context_weak_subject(context)

    if detected_subjects and study_hours:
        per_subject = max(round(study_hours / max(len(detected_subjects), 1), 1), 0.5)
        first_subject = priority_subject or detected_subjects[0]
        response = [
            f"Start with {first_subject} because it should get the first focused block.",
            f"With {study_hours} study hours, keep about {per_subject} hours for each main subject.",
        ]
        if weak_subject and weak_subject not in response[0]:
            response.append(f"Keep an extra short block for {weak_subject} because it is your weak subject.")
        response.append("Use the first block for concepts, the second for questions, and the last 20 minutes for revision.")
        if exam_days is not None:
            if exam_days <= 3:
                response.append("Since the exam is very close, shift more time to practice and revision than new topics.")
            elif exam_days <= 7:
                response.append("Since the exam is within a week, keep one revision block every day.")
        return " ".join(response)

    if study_hours:
        first_subject = priority_subject or weak_subject or "your priority subject"
        return (
            f"With {study_hours} study hours, begin with {first_subject}, keep the middle block for practice, "
            "and finish with revision. Avoid switching between too many subjects in one day."
        )

    if priority_subject:
        return (
            f"Start with {priority_subject}, then move to {weak_subject or 'your next weakest subject'}, "
            "and end with a short revision block."
        )

    return (
        "Make a simple order: urgent subject first, weak subject second, and revision last. "
        "If you tell me your study hours or exam days, I can make it more specific."
    )


def _build_weak_subject_response(lower_message, context):
    subjects = [_format_subject(subject) for subject in _extract_subjects(lower_message)]
    weak_subject = _context_weak_subject(context)

    if subjects:
        return (
            f"If {subjects[0]} feels weak, give it the first study block, solve questions on it daily, "
            "and revise it again before ending the session."
        )

    if weak_subject:
        status = _status_label(_context_latest_status(context, weak_subject))
        return (
            f"Right now {weak_subject} looks like your weak subject. Its latest progress is {status}, "
            "so start with it first and revisit it every day until it becomes stable."
        )

    return (
        "Your weak subject is usually the one with low progress, many pending topics, and a near exam. "
        "Give that subject more time, start with it first, and revisit it every day."
    )


def _build_revision_response(lower_message, context):
    exam_days = _extract_number(r"(\d+)\s*(?:days|day)", lower_message)
    priority_subject = _context_priority_subject(context)
    if exam_days is not None and exam_days <= 3:
        if priority_subject:
            return (
                f"Do fast revision now and begin with {priority_subject}. Focus on previous questions, formulas, "
                "short notes, and active recall. Do not start too many new topics at this stage."
            )
        return (
            "Do fast revision now: previous questions, formulas, short notes, and active recall. "
            "Do not start too many new topics at this stage."
        )
    return (
        "Use a revision cycle of recall, questions, and quick note review. "
        "Revise hard subjects first and repeat weak topics after a short break."
    )


def _build_exam_response(lower_message, context):
    exam_days = _extract_number(r"(\d+)\s*(?:days|day)", lower_message)
    priority_subject = _context_priority_subject(context)
    weak_subject = _context_weak_subject(context)
    if exam_days is None:
        if priority_subject:
            return (
                f"For exam preparation, start with {priority_subject}. After that, give time to {weak_subject or 'your weak areas'} "
                "and end with a revision round."
            )
        return "For exam preparation, start with subjects that have the nearest date, more topics, and lower confidence."
    if exam_days <= 3:
        return (
            f"Only {exam_days} days left means you should focus on revision, important questions, and weak areas. "
            f"Start with {priority_subject or 'the most urgent subject'} and keep the plan short and sharp."
        )
    if exam_days <= 7:
        return f"With {exam_days} days left, finish important topics first and keep one revision session daily."
    return f"With {exam_days} days left, divide your time between concept study, practice, and weekly revision."


def _build_focus_response(context):
    priority_subject = _context_priority_subject(context)
    if priority_subject:
        return (
            f"Use a focused cycle: 50 minutes on {priority_subject}, 10 minutes break, phone away, and one clear target per session. "
            "Finish the most difficult task before checking anything distracting."
        )
    return (
        "Use a focused cycle: 50 minutes study, 10 minutes break, phone away, and one clear target per session. "
        "Finish the most difficult task before checking anything distracting."
    )


def _build_recommendation_response(lower_message, context):
    subjects = [_format_subject(subject) for subject in _extract_subjects(lower_message)]
    if subjects:
        return (
            f"I would recommend starting with {subjects[0]} if it is weak or urgent, then move to practice, "
            "and close with a short revision round."
        )
    priority_subject = _context_priority_subject(context)
    weak_subject = _context_weak_subject(context)
    if priority_subject:
        return (
            f"I recommend starting with {priority_subject}. Then study {weak_subject or 'the next weak subject'} "
            "and keep the final block for revision."
        )
    return "I recommend studying the subject with the nearest exam and the highest pending workload first."


def _build_progress_response(context):
    if not context or not context.get("latest_status_map"):
        return "Track a few study updates first, then I can tell you which subjects are strong, partial, or pending."

    parts = []
    weak_subject = _context_weak_subject(context)
    priority_subject = _context_priority_subject(context)

    if weak_subject:
        parts.append(f"Weak subject: {weak_subject}.")
    if priority_subject:
        parts.append(f"Priority subject: {priority_subject}.")

    shown = 0
    for subject, status in context["latest_status_map"].items():
        if shown >= 3:
            break
        parts.append(f"{subject} is {_status_label(status)}.")
        shown += 1

    return " ".join(parts)


def get_ai_response(user_input, context=None):
    message = (user_input or "").strip()
    lower_message = message.lower()

    if not message:
        if context and _context_subjects(context):
            return (
                f"Ask me about your plan, weak subject, revision, or exams. "
                f"Your current subjects include {', '.join(_context_subjects(context)[:4])}."
            )
        return "Ask me about study planning, revision, weak subjects, exams, or productivity."

    if any(word in lower_message for word in ["plan", "schedule", "timetable", "routine"]):
        return _build_plan_response(message, lower_message, context)

    if any(word in lower_message for word in ["weak subject", "weakness", "weak area", "difficult subject"]):
        return _build_weak_subject_response(lower_message, context)

    if any(word in lower_message for word in ["revision", "revise", "review"]):
        return _build_revision_response(lower_message, context)

    if any(word in lower_message for word in ["exam", "test", "paper"]):
        return _build_exam_response(lower_message, context)

    if any(word in lower_message for word in ["motivation", "focus", "productivity", "concentration", "lazy"]):
        return _build_focus_response(context)

    if any(word in lower_message for word in ["recommend", "priority", "what should i study first", "first subject"]):
        return _build_recommendation_response(lower_message, context)

    if any(word in lower_message for word in ["progress", "status", "how am i doing"]):
        return _build_progress_response(context)

    subjects = [_format_subject(subject) for subject in _extract_subjects(lower_message)]
    if subjects:
        return (
            f"You mentioned {', '.join(subjects)}. Based on your current data, "
            f"start with {_context_priority_subject(context) or subjects[0]} and keep revision at the end."
        )

    if context and _context_subjects(context):
        return (
            f"I can help using your real study data. Right now your main subjects include "
            f"{', '.join(_context_subjects(context)[:4])}, and your current priority is "
            f"{_context_priority_subject(context) or 'not decided yet'}."
        )
    return (
        "I can help with study plans, revision strategy, exam preparation, weak subjects, and productivity. "
        "Tell me your subject, study hours, or exam days for a sharper answer."
    )
