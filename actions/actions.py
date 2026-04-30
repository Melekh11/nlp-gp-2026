from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Text, Tuple

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict


ROLE_LABELS = {
    "project_manager": "Project Manager",
    "data_analyst": "Data Analyst",
    "data_engineer": "Data Engineer",
    "data_scientist": "Data Scientist",
    "mlops_engineer": "MLOps Engineer",
    "unknown": "Не определена",
}

ROLE_DETAILS = {
    "project_manager": "Для Project Manager важны управление командой, коммуникация с бизнесом, планирование, работа со сроками и рисками, фасилитация, Jira/Scrum/Agile.",
    "data_analyst": "Для Data Analyst важны SQL, продуктовые метрики, статистика, A/B-тесты, дашборды, Excel, Power BI или Tableau.",
    "data_engineer": "Для Data Engineer важны SQL, Python, ETL, Airflow, Spark, Kafka, хранилища, витрины данных и контроль качества данных.",
    "data_scientist": "Для Data Scientist важны Python, статистика, ML, sklearn, PyTorch или TensorFlow, эксперименты и оценка качества моделей.",
    "mlops_engineer": "Для MLOps Engineer важны Docker, Kubernetes, CI/CD, MLflow, мониторинг, деплой моделей и production-инфраструктура.",
}

ROLE_ALIASES = {
    "pm": "project_manager",
    "project manager": "project_manager",
    "project_manager": "project_manager",
    "проджект": "project_manager",
    "проджект менеджер": "project_manager",
    "проджект менеджера": "project_manager",
    "продж": "project_manager",
    "проджа": "project_manager",
    "пм": "project_manager",
    "пму": "project_manager",
    "проектный менеджер": "project_manager",
    "менеджер проекта": "project_manager",
    "data analyst": "data_analyst",
    "data_analyst": "data_analyst",
    "аналитик": "data_analyst",
    "аналитик данных": "data_analyst",
    "bi аналитик": "data_analyst",
    "data engineer": "data_engineer",
    "data_engineer": "data_engineer",
    "инженер данных": "data_engineer",
    "дата инженер": "data_engineer",
    "data scientist": "data_scientist",
    "data_scientist": "data_scientist",
    "ds": "data_scientist",
    "дата сайентист": "data_scientist",
    "ml engineer": "data_scientist",
    "mlops": "mlops_engineer",
    "mlops engineer": "mlops_engineer",
    "mlops_engineer": "mlops_engineer",
    "инженер mlops": "mlops_engineer",
}

SKILL_ALIASES = {
    "python": "python",
    "питон": "python",
    "пайтон": "python",
    "sql": "sql",
    "pandas": "pandas",
    "numpy": "numpy",
    "sklearn": "sklearn",
    "scikit": "sklearn",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "машинное обучение": "ml",
    "machine learning": "ml",
    "ml": "ml",
    "airflow": "airflow",
    "spark": "spark",
    "kafka": "kafka",
    "etl": "etl",
    "elt": "etl",
    "dwh": "dwh",
    "хранилище": "dwh",
    "витрин": "dwh",
    "docker": "docker",
    "докер": "docker",
    "докера": "docker",
    "kubernetes": "kubernetes",
    "кубер": "kubernetes",
    "кубером": "kubernetes",
    "k8s": "kubernetes",
    "ci/cd": "ci_cd",
    "cicd": "ci_cd",
    "mlflow": "mlflow",
    "dvc": "dvc",
    "monitoring": "monitoring",
    "мониторинг": "monitoring",
    "prometheus": "monitoring",
    "grafana": "monitoring",
    "tableau": "tableau",
    "power bi": "power_bi",
    "excel": "excel",
    "a/b": "ab_testing",
    "ab тест": "ab_testing",
    "статист": "statistics",
    "jira": "jira",
    "scrum": "scrum",
    "agile": "agile",
    "stakeholder": "stakeholders",
    "стейкхол": "stakeholders",
    "бизнес": "stakeholders",
    "управлять людьми": "people_management",
    "управление людьми": "people_management",
    "управлял людьми": "people_management",
    "управляла людьми": "people_management",
    "управление команд": "people_management",
    "вести команд": "people_management",
    "руковод": "people_management",
    "тимлид": "people_management",
    "лид": "people_management",
    "soft skills": "communication",
    "софт": "communication",
    "коммуникац": "communication",
    "общаться": "communication",
    "переговор": "communication",
    "презентац": "presentation",
    "публичн": "presentation",
    "срок": "planning",
    "планирован": "planning",
    "roadmap": "planning",
    "роадмап": "planning",
    "риски": "risk_management",
    "risk": "risk_management",
    "требован": "requirements",
    "бриф": "requirements",
    "кейсы": "case_solving",
    "кейс": "case_solving",
    "case": "case_solving",
    "чемпионат": "case_solving",
    "кодить": "coding_basic",
    "код": "coding_basic",
    "программир": "coding_basic",
    "ответствен": "ownership",
    "организ": "ownership",
}

ROLE_SKILL_WEIGHTS = {
    "project_manager": {
        "stakeholders": 18,
        "people_management": 18,
        "communication": 14,
        "planning": 14,
        "risk_management": 12,
        "requirements": 10,
        "presentation": 8,
        "case_solving": 6,
        "ownership": 8,
        "scrum": 14,
        "agile": 12,
        "jira": 10,
        "statistics": 3,
        "sql": 3,
        "python": 2,
        "coding_basic": 2,
    },
    "data_analyst": {
        "sql": 18,
        "statistics": 15,
        "ab_testing": 12,
        "tableau": 12,
        "power_bi": 12,
        "excel": 7,
        "python": 8,
        "pandas": 8,
        "stakeholders": 6,
        "communication": 4,
        "case_solving": 8,
        "presentation": 4,
    },
    "data_engineer": {
        "sql": 10,
        "python": 10,
        "airflow": 18,
        "spark": 16,
        "kafka": 14,
        "etl": 18,
        "dwh": 14,
        "docker": 5,
        "coding_basic": 4,
    },
    "data_scientist": {
        "python": 15,
        "sql": 6,
        "pandas": 8,
        "numpy": 6,
        "statistics": 12,
        "ml": 18,
        "sklearn": 12,
        "pytorch": 12,
        "tensorflow": 10,
        "ab_testing": 4,
        "case_solving": 4,
        "coding_basic": 4,
    },
    "mlops_engineer": {
        "python": 8,
        "docker": 16,
        "kubernetes": 18,
        "ci_cd": 16,
        "mlflow": 12,
        "dvc": 10,
        "monitoring": 12,
        "airflow": 5,
        "ml": 5,
    },
}

SALARY_LIMITS = {
    "project_manager": 320000,
    "data_analyst": 240000,
    "data_engineer": 340000,
    "data_scientist": 360000,
    "mlops_engineer": 380000,
}

QUESTION_BY_SLOT = {
    "target_role": "На какую позицию вы хотите пройти собеседование?",
    "experience_years": "Сколько лет релевантного опыта у вас есть?",
    "skills": "Перечислите ключевые навыки и инструменты.",
    "project_types": "Расскажите о 1-2 самых релевантных проектах: тип проекта, данные, инструменты, результат.",
    "project_role": "Какую роль вы выполняли в проектах: менеджер, аналитик, разработчик или лид?",
    "education_text": "Какое у вас образование или профильная подготовка?",
    "english_level": "Какой у вас уровень английского?",
    "work_format": "Какой формат работы вам подходит: офис, удаленно, гибрид или любой?",
    "salary_expectation_min": "Какие зарплатные ожидания? Можно указать диапазон.",
    "availability": "Когда готовы выйти на работу?",
}


def text_of(tracker: Tracker) -> str:
    return (tracker.latest_message.get("text") or "").strip()


def lower_text(tracker: Tracker) -> str:
    return text_of(tracker).lower().replace("ё", "е")


def entities(tracker: Tracker, name: str) -> List[Any]:
    return [e.get("value") for e in tracker.latest_message.get("entities", []) if e.get("entity") == name]


def unique(values: List[Any]) -> List[Any]:
    result = []
    for value in values:
        if value is None:
            continue
        item = str(value).strip()
        if item and item not in result:
            result.append(item)
    return result


def normalize_role(value: Any) -> str:
    if not value:
        return "unknown"
    raw = str(value).strip().lower().replace("-", " ").replace("_", " ")
    return ROLE_ALIASES.get(raw, "unknown")


def infer_role(text: str) -> str:
    for alias, role in ROLE_ALIASES.items():
        if alias in text:
            return role
    if any(token in text for token in ["не знаю", "подбери", "не определился", "любая"]):
        return "unknown"
    return "unknown"


def parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).lower().replace(",", ".").replace(" ", "")
    match = re.search(r"\d+(\.\d+)?", raw)
    if not match:
        return None
    number = float(match.group(0))
    if any(unit in raw for unit in ["к", "k", "тыс"]):
        number *= 1000
    return number


def parse_years(text: str, values: List[Any]) -> Optional[float]:
    for value in values:
        number = parse_number(value)
        if number is not None and number <= 50:
            return number
    if any(phrase in text for phrase in ["без опыта", "нет опыта", "опыта нет", "не было опыта", "давай пропустим", "пропустим"]):
        return 0.0
    if "меньше года" in text:
        return 0.5
    match = re.search(r"(\d+([\.,]\d+)?)\s*(год|лет|года)", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def parse_salary(text: str, values: List[Any]) -> Tuple[Optional[float], Optional[float]]:
    has_signal = bool(values) or any(word in text for word in ["зарплат", "ожидан", "руб", "тыс", "оклад", "доход"]) or bool(re.search(r"\d+([\.,]\d+)?\s*(к|k)\b", text))
    if not has_signal:
        return None, None
    numbers = []
    for value in values:
        number = parse_number(value)
        if number is not None:
            if number < 1000:
                number *= 1000
            numbers.append(number)
    if not numbers:
        for match in re.finditer(r"\d+([\.,]\d+)?\s*(к|k|тыс|тысяч|руб|рублей)?", text):
            number = parse_number(match.group(0))
            if number is not None:
                if number < 1000:
                    number *= 1000
                numbers.append(number)
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], None
    return min(numbers), max(numbers)


def infer_skills(text: str, explicit: List[Any], allow_free_text: bool = False) -> List[str]:
    values = [str(value).lower() for value in explicit]
    for alias, skill in SKILL_ALIASES.items():
        if alias in text:
            values.append(skill)
    if allow_free_text and not values and len(text.split()) >= 3 and not text.endswith("?"):
        values.append("free_text_skills")
    return unique(values)


def infer_projects(text: str, explicit: List[Any]) -> List[str]:
    values = [str(value).lower() for value in explicit]
    if any(phrase in text for phrase in ["проектов нет", "нет проектов", "без проектов", "не было проектов"]) or ("бариста" in text and "проект" not in text):
        return ["no_relevant_projects"]
    checks = {
        "etl": ["etl", "пайплайн", "pipeline", "airflow", "spark", "kafka"],
        "analytics": ["дашборд", "метрик", "bi", "ab", "a/b", "аналит"],
        "ml_model": ["модель", "ml", "классификац", "регресс", "прогноз", "рекоменд"],
        "production_ml": ["production", "продакшн", "деплой", "инференс", "monitoring", "мониторинг"],
        "management": ["управлял", "команд", "срок", "рис", "стейкхол", "stakeholder"],
        "pet_project": ["pet", "учебн", "курсов", "домашн"],
    }
    for project, keywords in checks.items():
        if any(keyword in text for keyword in keywords):
            values.append(project)
    return unique(values)


def has_project_context(text: str) -> bool:
    return any(
        word in text
        for word in [
            "проект",
            "делал",
            "делала",
            "пилил",
            "строил",
            "собирал",
            "обучал",
            "выкатывал",
            "вел ",
            "вела ",
            "занимался",
            "занималась",
            "production",
            "продакшн",
        ]
    )


def is_skip_like(text: str) -> bool:
    return any(phrase in text for phrase in ["не знаю", "не уверен", "пропустим", "давай пропустим", "затрудняюсь"])


def is_out_of_scope_text(text: str) -> bool:
    return any(word in text for word in ["погода", "курс доллара", "новости", "анекдот", "сколько времени", "который час"])


def is_role_skill_question(text: str) -> bool:
    return text.endswith("?") and any(word in text for word in ["навык", "скилл", "уметь", "требован"]) and infer_role(text) != "unknown"


def infer_project_role(text: str, value: Any = None) -> str:
    raw = str(value or "").lower()
    if raw in {"manager", "analyst", "developer", "lead"}:
        return raw
    if any(word in text for word in ["менедж", "управля", "координир", "срок", "рис"]):
        return "manager"
    if any(word in text for word in ["аналит", "метрик", "дашборд", "гипотез"]):
        return "analyst"
    if any(word in text for word in ["лид", "lead", "руковод", "тимлид"]):
        return "lead"
    if any(word in text for word in ["разраб", "инженер", "код", "строил", "делал"]):
        return "developer"
    if any(phrase in text for phrase in ["никакая роль", "роли не было", "не было роли", "нет роли"]):
        return "unknown"
    return "unknown"


def infer_complexity(text: str) -> str:
    high = ["production", "highload", "kubernetes", "spark", "kafka", "команда", "миллион", "мониторинг", "продакшн"]
    low = ["учебн", "pet", "простой", "курсов", "домашн"]
    if any(word in text for word in high):
        return "high"
    if any(word in text for word in low):
        return "low"
    if any(word in text for word in ["проект", "модель", "пайплайн", "дашборд"]):
        return "medium"
    return "unknown"


def normalize_english(text: str, value: Any = None) -> str:
    raw = str(value or text).lower()
    for level in ["c2", "c1", "b2", "b1", "a2", "a1"]:
        if level in raw:
            return level
    if any(word in raw for word in ["нет", "никак", "не знаю"]):
        return "none"
    if any(word in raw for word in ["свобод", "advanced", "fluent"]):
        return "c1"
    if any(word in raw for word in ["upper intermediate", "выше среднего"]):
        return "b2"
    if any(word in raw for word in ["документац", "доку", "док", "intermediate", "средний", "разговорный", "нормально"]):
        return "b1"
    return "unknown"


def normalize_work_format(text: str, value: Any = None) -> str:
    raw = str(value or text).lower()
    if any(word in raw for word in ["remote", "удален", "дистан"]):
        return "remote"
    if any(word in raw for word in ["hybrid", "гибрид"]):
        return "hybrid"
    if any(word in raw for word in ["office", "офис"]):
        return "office"
    if any(word in raw for word in ["любой", "без разницы", "any"]):
        return "any"
    return "unknown"


def normalize_availability(text: str, value: Any = None) -> str:
    raw = str(value or text).lower()
    if any(word in raw for word in ["сразу", "сейчас", "now", "немедленно", "хоть завтра", "завтра"]):
        return "available_now"
    if any(word in raw for word in ["три месяца", "3 месяца", "не раньше", "не готов", "позже"]):
        return "available_not_soon"
    if any(word in raw for word in ["недел", "месяц", "скоро", "отрабаты"]):
        return "available_soon"
    return "unknown"


def infer_education(text: str) -> Tuple[List[str], List[str]]:
    levels = []
    fields = []
    if any(word in text for word in ["магистр", "магистрат"]):
        levels.append("master")
    if any(word in text for word in ["бакалавр", "бакалавриат"]):
        levels.append("bachelor")
    if any(word in text for word in ["высш", "университет", "институт"]):
        levels.append("higher")
    if any(word in text for word in ["курс", "сертифик", "сам"]):
        levels.append("courses")
    if any(word in text for word in ["информ", "программ", "математ", "физмат", "computer"]):
        fields.append("technical")
    if any(word in text for word in ["эконом", "бизнес", "менедж"]):
        fields.append("business")
    if any(word in text for word in ["машин", "data", "аналит", "ml"]):
        fields.append("data")
    return unique(levels), unique(fields)


def extract_facts(tracker: Tracker) -> Dict[str, Any]:
    text = lower_text(tracker)
    requested_slot = tracker.get_slot("requested_slot")
    facts: Dict[str, Any] = {}
    role = normalize_role((entities(tracker, "target_role") or [None])[0])
    if role == "unknown":
        role = infer_role(text)
    if role != "unknown":
        facts["target_role"] = role
    years = parse_years(text, entities(tracker, "experience_years")) if requested_slot == "experience_years" or entities(tracker, "experience_years") else None
    if years is not None:
        facts["experience_years"] = years
    skills = infer_skills(text, entities(tracker, "skill"), allow_free_text=requested_slot == "skills")
    if skills:
        current = tracker.get_slot("skills") or []
        facts["skills"] = unique(current + skills)
    projects = infer_projects(text, entities(tracker, "project_type")) if requested_slot == "project_types" or has_project_context(text) else []
    if projects:
        current_projects = tracker.get_slot("project_types") or []
        facts["project_types"] = unique(current_projects + projects)
        facts["project_complexity"] = infer_complexity(text)
    project_role = infer_project_role(text, (entities(tracker, "project_role") or [None])[0]) if requested_slot == "project_role" or any(word in text for word in ["лид", "менедж", "разработ", "аналит", "управлял", "управляла"]) else "unknown"
    if project_role != "unknown":
        facts["project_role"] = project_role
    english = normalize_english(text, (entities(tracker, "english_level") or [None])[0]) if requested_slot == "english_level" or entities(tracker, "english_level") else "unknown"
    if english != "unknown":
        facts["english_level"] = english
    work_format = normalize_work_format(text, (entities(tracker, "work_format") or [None])[0]) if requested_slot == "work_format" or entities(tracker, "work_format") else "unknown"
    if work_format != "unknown":
        facts["work_format"] = work_format
    availability = normalize_availability(text, (entities(tracker, "availability") or [None])[0]) if requested_slot == "availability" or entities(tracker, "availability") else "unknown"
    if availability != "unknown":
        facts["availability"] = availability
    if requested_slot == "salary_expectation_min" and "миллион" in text:
        facts["salary_expectation_min"] = 1000000.0
        facts["salary_expectation_max"] = None
        return facts
    salary_min, salary_max = parse_salary(text, entities(tracker, "salary_amount")) if requested_slot == "salary_expectation_min" or entities(tracker, "salary_amount") else (None, None)
    if salary_min is not None:
        facts["salary_expectation_min"] = salary_min
        facts["salary_expectation_max"] = salary_max
    return facts


def score_candidate(slots: Dict[str, Any], tie_answer: Optional[str] = None) -> Dict[str, Any]:
    skills = set(slots.get("skills") or [])
    projects = set(slots.get("project_types") or [])
    project_role = slots.get("project_role") or "unknown"
    complexity = slots.get("project_complexity") or "unknown"
    target_role = slots.get("target_role") or "unknown"
    english = slots.get("english_level") or "unknown"
    education_fields = set(slots.get("education_field") or [])
    years = float(slots.get("experience_years") or 0)
    tie_text = (tie_answer or "").lower()
    scores: Dict[str, float] = {}
    reasons: Dict[str, List[str]] = {}
    for role, weights in ROLE_SKILL_WEIGHTS.items():
        score = min(years * 6, 24)
        role_reasons = []
        matched = []
        for skill, weight in weights.items():
            if skill in skills:
                score += weight
                matched.append(skill)
        if matched:
            role_reasons.append("релевантные навыки: " + ", ".join(matched[:5]))
        if role == target_role:
            score += 8
            role_reasons.append("кандидат целится в эту роль")
        if role == "project_manager" and project_role in {"manager", "lead"}:
            score += 18
            role_reasons.append("есть управленческая роль в проектах")
        if role == "data_analyst" and ("analytics" in projects or project_role == "analyst"):
            score += 18
            role_reasons.append("есть аналитические проекты или роль аналитика")
        if role == "data_engineer" and ("etl" in projects or "dwh" in skills):
            score += 20
            role_reasons.append("есть опыт data pipelines или DWH")
        if role == "data_scientist" and "ml_model" in projects:
            score += 20
            role_reasons.append("есть опыт ML-моделей")
        if role == "mlops_engineer" and "production_ml" in projects:
            score += 20
            role_reasons.append("есть production/MLOps опыт")
        if complexity == "high":
            score += 8
            role_reasons.append("проекты высокой сложности")
        elif complexity == "medium":
            score += 4
        elif complexity == "low":
            score -= 6
        if "technical" in education_fields and role in {"data_engineer", "data_scientist", "mlops_engineer"}:
            score += 5
        if "data" in education_fields and role in {"data_analyst", "data_scientist"}:
            score += 5
        if english in {"b2", "c1", "c2"}:
            score += 4
        elif english in {"none", "a1"}:
            score -= 4
        if tie_text:
            tie_boosts = {
                "project_manager": ["управ", "команд", "коммуникац", "stakeholder"],
                "data_analyst": ["bi", "аналит", "метрик", "дашборд", "гипотез"],
                "data_engineer": ["пайплайн", "pipeline", "etl", "данных", "инженер"],
                "data_scientist": ["ml", "модель", "исслед", "эксперимент"],
                "mlops_engineer": ["production", "инфраструкт", "эксплуатац", "деплой", "kubernetes"],
            }
            if any(word in tie_text for word in tie_boosts[role]):
                score += 10
                role_reasons.append("tie-breaker ответ усилил роль")
        scores[role] = max(0, min(round(score, 1), 100))
        reasons[role] = role_reasons or ["профиль частично пересекается с ролью"]
    ranking = sorted(
        [{"role": role, "label": ROLE_LABELS[role], "score": score, "reasons": reasons[role]} for role, score in scores.items()],
        key=lambda item: item["score"],
        reverse=True,
    )
    top = ranking[0]
    second = ranking[1]
    if top["score"] >= 65:
        decision = "fit"
    elif top["score"] >= 45:
        decision = "borderline"
    else:
        decision = "reject"
    tie_question = None
    if top["score"] >= 45 and abs(top["score"] - second["score"]) <= 7 and not tie_answer:
        tie_question = make_tie_question(top["role"], second["role"])
    risks = make_risks(slots, top["role"], top["score"])
    return {
        "ranking": ranking,
        "recommended_role": top["role"],
        "decision_status": decision,
        "risk_flags": risks,
        "tie_breaker_question": tie_question,
    }


def make_tie_question(first: str, second: str) -> str:
    pair = {first, second}
    if pair == {"data_engineer", "mlops_engineer"}:
        return "Уточнение: вам ближе строить data pipelines или отвечать за production-инфраструктуру и эксплуатацию моделей?"
    if pair == {"data_analyst", "data_scientist"}:
        return "Уточнение: вам ближе BI, метрики и гипотезы или обучение и улучшение ML-моделей?"
    if pair == {"data_scientist", "mlops_engineer"}:
        return "Уточнение: вам ближе исследовать модели или выводить их в production и мониторить?"
    if pair == {"project_manager", "data_analyst"}:
        return "Уточнение: вам ближе управлять командой и сроками или самостоятельно анализировать данные и метрики?"
    return f"Уточнение: что вам ближе — {ROLE_LABELS[first]} или {ROLE_LABELS[second]}?"


def make_risks(slots: Dict[str, Any], top_role: str, top_score: float) -> List[str]:
    risks = []
    skills = set(slots.get("skills") or [])
    years = float(slots.get("experience_years") or 0)
    salary = slots.get("salary_expectation_min")
    english = slots.get("english_level") or "unknown"
    availability = slots.get("availability") or "unknown"
    target_role = slots.get("target_role") or "unknown"
    complexity = slots.get("project_complexity") or "unknown"
    if top_score < 45:
        risks.append("низкое соответствие всем пяти ролям")
    if years < 1:
        risks.append("мало релевантного опыта")
    if target_role not in {"unknown", top_role}:
        risks.append("желаемая роль отличается от рекомендованной")
    if salary and salary > SALARY_LIMITS.get(top_role, 300000):
        risks.append("зарплатные ожидания выше типичного диапазона роли")
    if english in {"none", "a1", "a2", "unknown"}:
        risks.append("английский может ограничить работу с документацией и международной командой")
    if availability == "available_not_soon":
        risks.append("кандидат доступен не скоро")
    if complexity == "low":
        risks.append("нет признаков проектов промышленной сложности")
    required = {
        "project_manager": {"stakeholders", "scrum", "jira"},
        "data_analyst": {"sql", "statistics"},
        "data_engineer": {"airflow", "etl"},
        "data_scientist": {"python", "ml"},
        "mlops_engineer": {"docker", "kubernetes", "ci_cd"},
    }
    missing = sorted(required[top_role] - skills)
    if missing:
        risks.append("не хватает ключевых сигналов роли: " + ", ".join(missing))
    return risks or ["критичных рисков не обнаружено"]


def build_candidate_summary(slots: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "target_role": ROLE_LABELS.get(slots.get("target_role") or "unknown"),
        "recommended_role": ROLE_LABELS.get(result["recommended_role"]),
        "decision_status": result["decision_status"],
        "experience_years": slots.get("experience_years"),
        "skills": slots.get("skills") or [],
        "project_types": slots.get("project_types") or [],
        "project_complexity": slots.get("project_complexity") or "unknown",
        "project_role": slots.get("project_role") or "unknown",
        "education": slots.get("education_text"),
        "english_level": slots.get("english_level") or "unknown",
        "work_format": slots.get("work_format") or "unknown",
        "salary_expectation_min": slots.get("salary_expectation_min"),
        "salary_expectation_max": slots.get("salary_expectation_max"),
        "availability": slots.get("availability") or "unknown",
    }


def build_recruiter_report(slots: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "candidate_summary": build_candidate_summary(slots, result),
        "role_ranking": result["ranking"],
        "recommended_role": result["recommended_role"],
        "decision_status": result["decision_status"],
        "risk_flags": result["risk_flags"],
        "next_step": next_step(result["decision_status"]),
    }


def next_step(decision: str) -> str:
    if decision == "fit":
        return "Передать на техническое интервью"
    if decision == "borderline":
        return "Провести короткий рекрутерский созвон и уточнить риски"
    return "Отправить вежливый отказ с рекомендациями по развитию"


def export_report(sender_id: str, report: Dict[str, Any]) -> Tuple[str, str]:
    export_dir = Path.cwd() / "exports"
    export_dir.mkdir(exist_ok=True)
    safe_sender = re.sub(r"[^a-zA-Z0-9_-]+", "_", sender_id or "candidate")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = export_dir / f"{safe_sender}_{stamp}.json"
    csv_path = export_dir / f"{safe_sender}_{stamp}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["candidate_summary"]
    row = {
        "created_at": report["created_at"],
        "recommended_role": report["recommended_role"],
        "decision_status": report["decision_status"],
        "top_score": report["role_ranking"][0]["score"],
        "risk_flags": "; ".join(report["risk_flags"]),
        "experience_years": summary.get("experience_years"),
        "skills": "; ".join(summary.get("skills") or []),
        "salary_expectation_min": summary.get("salary_expectation_min"),
        "availability": summary.get("availability"),
        "next_step": report["next_step"],
    }
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    return str(json_path), str(csv_path)


def finalize(dispatcher: CollectingDispatcher, tracker: Tracker, slots: Dict[str, Any], result: Dict[str, Any]) -> List[SlotSet]:
    report = build_recruiter_report(slots, result)
    json_path, csv_path = export_report(tracker.sender_id, report)
    top_roles = ", ".join(item["label"] for item in result["ranking"][:2])
    if result["decision_status"] == "fit":
        decision_text = f"Спасибо, интервью завершено. По вашему опыту наиболее релевантное направление: {ROLE_LABELS[result['recommended_role']]}. Также можно рассмотреть: {top_roles}."
    elif result["decision_status"] == "borderline":
        decision_text = f"Спасибо, интервью завершено. Я передам ваши ответы рекрутеру для дополнительного рассмотрения. Ближайшие по профилю направления: {top_roles}."
    else:
        decision_text = "Спасибо, интервью завершено. Сейчас я не вижу достаточного совпадения с открытыми позициями, но ваши ответы будут сохранены для рекрутера."
    dispatcher.utter_message(
        text=(
            f"{decision_text}\n"
            "Следующий шаг: с вами свяжутся, если профиль подойдет под текущие вакансии."
        )
    )
    return [
        SlotSet("candidate_summary", report["candidate_summary"]),
        SlotSet("recruiter_report", report),
        SlotSet("role_ranking", result["ranking"]),
        SlotSet("risk_flags", result["risk_flags"]),
        SlotSet("decision_status", result["decision_status"]),
        SlotSet("recommended_role", result["recommended_role"]),
        SlotSet("tie_breaker_question", None),
        SlotSet("export_path_json", json_path),
        SlotSet("export_path_csv", csv_path),
    ]


class ValidateInterviewForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_interview_form"

    async def extract_target_role(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        facts = extract_facts(tracker)
        facts["target_role"] = facts.get("target_role") or "unknown"
        return facts

    async def extract_experience_years(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "experience_years" and not entities(tracker, "experience_years"):
            return {}
        text = lower_text(tracker)
        if is_out_of_scope_text(text):
            dispatcher.utter_message(text="Давайте вернемся к интервью. Сейчас важно понять ваш релевантный опыт.")
            return {"experience_years": None}
        if is_skip_like(text) or any(word in text for word in ["бариста", "студент", "учусь"]):
            return {"experience_years": 0.0}
        return extract_facts(tracker)

    async def extract_skills(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "skills" and not entities(tracker, "skill"):
            return {}
        text = lower_text(tracker)
        if is_role_skill_question(text):
            role = infer_role(text)
            dispatcher.utter_message(text=ROLE_DETAILS[role])
            return {"skills": None}
        if is_skip_like(text):
            return {"skills": ["not_specified"]}
        return extract_facts(tracker)

    async def extract_project_types(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "project_types" and not entities(tracker, "project_type"):
            return {}
        if is_skip_like(lower_text(tracker)):
            return {"project_types": ["not_specified"], "project_complexity": "unknown", "project_role": "unknown"}
        facts = extract_facts(tracker)
        if "no_relevant_projects" in facts.get("project_types", []):
            facts["project_role"] = "unknown"
        return facts

    async def extract_project_role(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "project_role" and not entities(tracker, "project_role"):
            return {}
        text = lower_text(tracker)
        if is_skip_like(text) or any(phrase in text for phrase in ["никакая роль", "роли не было", "нет роли"]):
            return {"project_role": "unknown"}
        return extract_facts(tracker)

    async def extract_education_text(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "education_text":
            return extract_facts(tracker)
        text = text_of(tracker)
        levels, fields = infer_education(text.lower().replace("ё", "е"))
        facts = extract_facts(tracker)
        facts.update({"education_text": text, "education_level": levels, "education_field": fields})
        return facts

    async def extract_english_level(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "english_level" and not entities(tracker, "english_level"):
            return {}
        if is_skip_like(lower_text(tracker)):
            return {"english_level": "unknown"}
        return extract_facts(tracker)

    async def extract_work_format(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "work_format" and not entities(tracker, "work_format"):
            return {}
        if is_skip_like(lower_text(tracker)):
            return {"work_format": "unknown"}
        return extract_facts(tracker)

    async def extract_salary_expectation_min(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "salary_expectation_min" and not entities(tracker, "salary_amount"):
            return {}
        return extract_facts(tracker)

    async def extract_availability(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "availability" and not entities(tracker, "availability"):
            return {}
        if is_skip_like(lower_text(tracker)):
            return {"availability": "unknown"}
        return extract_facts(tracker)

    def validate_target_role(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"target_role": slot_value or "unknown"}

    def validate_experience_years(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            if not is_out_of_scope_text(lower_text(tracker)):
                dispatcher.utter_message(text="Укажите опыт числом лет, например: 3 года. Если релевантного опыта нет, можно так и написать.")
            return {"experience_years": None}
        return {"experience_years": max(0.0, min(float(slot_value), 50.0))}

    def validate_skills(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value:
            if not is_role_skill_question(lower_text(tracker)):
                dispatcher.utter_message(text="Перечислите хотя бы несколько навыков или инструментов.")
            return {"skills": None}
        return {"skills": slot_value}

    def validate_project_types(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="Расскажите хотя бы об одном проекте или напишите, что проектов пока не было.")
            return {"project_types": None, "project_complexity": None}
        return {"project_types": slot_value}

    def validate_project_role(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value or slot_value == "unknown":
            if "no_relevant_projects" in (tracker.get_slot("project_types") or []):
                return {"project_role": "unknown"}
            dispatcher.utter_message(text="Уточните вашу роль в проектах: управляли, анализировали, разрабатывали или лидировали?")
            return {"project_role": None}
        return {"project_role": slot_value}

    def validate_education_text(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"education_text": slot_value or "unknown"}

    def validate_english_level(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"english_level": slot_value or "unknown"}

    def validate_work_format(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"work_format": slot_value or "unknown"}

    def validate_salary_expectation_min(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text="Укажите зарплатные ожидания числом или диапазоном.")
            return {"salary_expectation_min": None}
        return {"salary_expectation_min": float(slot_value)}

    def validate_availability(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"availability": slot_value or "unknown"}


class ActionRankCandidate(Action):
    def name(self) -> Text:
        return "action_rank_candidate"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slots = tracker.current_slot_values()
        result = score_candidate(slots)
        if result["tie_breaker_question"]:
            dispatcher.utter_message(text=f"Хочу уточнить, чтобы точнее сопоставить ваш опыт с вакансией. {result['tie_breaker_question']}")
            return [
                SlotSet("role_ranking", result["ranking"]),
                SlotSet("risk_flags", result["risk_flags"]),
                SlotSet("decision_status", result["decision_status"]),
                SlotSet("recommended_role", result["recommended_role"]),
                SlotSet("tie_breaker_question", result["tie_breaker_question"]),
            ]
        return finalize(dispatcher, tracker, slots, result)


class ActionApplyTieBreaker(Action):
    def name(self) -> Text:
        return "action_apply_tie_breaker"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not tracker.get_slot("tie_breaker_question"):
            dispatcher.utter_message(text="Сейчас нет активного уточняющего вопроса. Можем продолжить интервью.")
            return []
        slots = tracker.current_slot_values()
        answer = text_of(tracker)
        result = score_candidate(slots, answer)
        events = finalize(dispatcher, tracker, slots, result)
        events.append(SlotSet("tie_breaker_answer", answer))
        return events


class ActionChangeAnswer(Action):
    def name(self) -> Text:
        return "action_change_answer"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text = lower_text(tracker)
        events: List[SlotSet] = []
        role = infer_role(text)
        years = parse_years(text, entities(tracker, "experience_years"))
        skills = infer_skills(text, entities(tracker, "skill"), allow_free_text=False)
        salary_min, salary_max = parse_salary(text, entities(tracker, "salary_amount"))
        english = normalize_english(text, (entities(tracker, "english_level") or [None])[0])
        work_format = normalize_work_format(text, (entities(tracker, "work_format") or [None])[0])
        availability = normalize_availability(text, (entities(tracker, "availability") or [None])[0])
        projects = infer_projects(text, entities(tracker, "project_type"))
        changed = []
        if role != "unknown":
            events.append(SlotSet("target_role", role))
            changed.append("роль")
        if years is not None:
            events.append(SlotSet("experience_years", years))
            changed.append("опыт")
        if skills:
            current = tracker.get_slot("skills") or []
            events.append(SlotSet("skills", unique(current + skills)))
            changed.append("навыки")
        if salary_min is not None:
            events.append(SlotSet("salary_expectation_min", salary_min))
            events.append(SlotSet("salary_expectation_max", salary_max))
            changed.append("зарплата")
        if english != "unknown":
            events.append(SlotSet("english_level", english))
            changed.append("английский")
        if work_format != "unknown":
            events.append(SlotSet("work_format", work_format))
            changed.append("формат работы")
        if availability != "unknown":
            events.append(SlotSet("availability", availability))
            changed.append("доступность")
        if projects:
            current_projects = tracker.get_slot("project_types") or []
            events.append(SlotSet("project_types", unique(current_projects + projects)))
            events.append(SlotSet("project_complexity", infer_complexity(text)))
            changed.append("проекты")
        if changed:
            dispatcher.utter_message(text="Обновил: " + ", ".join(changed) + ".")
        else:
            dispatcher.utter_message(text="Не понял, что именно нужно изменить. Например: изменить зарплатные ожидания на 250к.")
        return events


class ActionRepeatQuestion(Action):
    def name(self) -> Text:
        return "action_repeat_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        requested_slot = tracker.get_slot("requested_slot")
        question = QUESTION_BY_SLOT.get(requested_slot)
        if question:
            dispatcher.utter_message(text=question)
        else:
            dispatcher.utter_message(text="Сейчас нет активного вопроса. Можно начать интервью или продолжить отклик.")
        return []


class ActionSkipQuestion(Action):
    def name(self) -> Text:
        return "action_skip_question"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        requested_slot = tracker.get_slot("requested_slot")
        if not requested_slot:
            dispatcher.utter_message(text="Сейчас нечего пропускать.")
            return []
        default_value: Any = "unknown"
        if requested_slot in {"skills", "project_types", "education_level", "education_field"}:
            default_value = ["unknown"]
        if requested_slot in {"experience_years", "salary_expectation_min", "salary_expectation_max"}:
            default_value = 0.0
        dispatcher.utter_message(text="Пропустил вопрос.")
        return [SlotSet(requested_slot, default_value)]


class ActionShowNextStep(Action):
    def name(self) -> Text:
        return "action_show_next_step"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        report = tracker.get_slot("recruiter_report")
        tie_question = tracker.get_slot("tie_breaker_question")
        if tie_question:
            dispatcher.utter_message(text="Сначала ответьте на уточняющий вопрос: " + tie_question)
            return []
        if not report:
            dispatcher.utter_message(text="Сначала нужно пройти короткое интервью.")
            return []
        top_roles = ", ".join(item["label"] for item in report["role_ranking"][:2])
        dispatcher.utter_message(
            text=(
                f"Ваш отклик принят. Наиболее близкие направления: {top_roles}.\n"
                "Если профиль подойдет под текущие вакансии, рекрутер свяжется с вами для следующего этапа."
            )
        )
        return []


class ActionShowRoleDetails(Action):
    def name(self) -> Text:
        return "action_show_role_details"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        role = normalize_role((entities(tracker, "target_role") or [None])[0])
        if role == "unknown":
            role = infer_role(lower_text(tracker))
        dispatcher.utter_message(text=ROLE_DETAILS.get(role, "Уточните роль: Project Manager, Data Analyst, Data Engineer, Data Scientist или MLOps Engineer."))
        return []
