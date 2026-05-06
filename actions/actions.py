from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
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
    "p m": "project_manager",
    "project manager": "project_manager",
    "project_manager": "project_manager",
    "projectmanager": "project_manager",
    "проджект": "project_manager",
    "проджект менеджер": "project_manager",
    "проджект менеджера": "project_manager",
    "проджект менеджером": "project_manager",
    "продж": "project_manager",
    "проджа": "project_manager",
    "прожект": "project_manager",
    "прожект менеджер": "project_manager",
    "пм": "project_manager",
    "пму": "project_manager",
    "пиэм": "project_manager",
    "проектный менеджер": "project_manager",
    "менеджер проекта": "project_manager",
    "data analyst": "data_analyst",
    "dataanalyst": "data_analyst",
    "data_analyst": "data_analyst",
    "да": "data_analyst",
    "аналитик": "data_analyst",
    "аналитик данных": "data_analyst",
    "аналитика данных": "data_analyst",
    "дата аналитик": "data_analyst",
    "дата аналитика": "data_analyst",
    "дата аналетик": "data_analyst",
    "bi аналитик": "data_analyst",
    "би аналитик": "data_analyst",
    "продуктовый аналитик": "data_analyst",
    "аналитик продукта": "data_analyst",
    "data engineer": "data_engineer",
    "dataengineer": "data_engineer",
    "data_engineer": "data_engineer",
    "де": "data_engineer",
    "инженер данных": "data_engineer",
    "дата инженер": "data_engineer",
    "дата инженера": "data_engineer",
    "дата инженером": "data_engineer",
    "дата инжинер": "data_engineer",
    "инженер данных": "data_engineer",
    "инжинер данных": "data_engineer",
    "data scientist": "data_scientist",
    "datascientist": "data_scientist",
    "data_scientist": "data_scientist",
    "ds": "data_scientist",
    "дс": "data_scientist",
    "дата сайнтист": "data_scientist",
    "дата сайентист": "data_scientist",
    "дата сайентиста": "data_scientist",
    "датасаентист": "data_scientist",
    "дата саентист": "data_scientist",
    "ml engineer": "data_scientist",
    "machine learning engineer": "data_scientist",
    "мл инженер": "data_scientist",
    "эмельщик": "data_scientist",
    "эмель инженер": "data_scientist",
    "mlops": "mlops_engineer",
    "mlops engineer": "mlops_engineer",
    "mlops_engineer": "mlops_engineer",
    "инженер mlops": "mlops_engineer",
    "млопс": "mlops_engineer",
    "млопса": "mlops_engineer",
    "млопс инженер": "mlops_engineer",
    "эмэлопс": "mlops_engineer",
    "эмельопс": "mlops_engineer",
    "мл ops": "mlops_engineer",
}

SKILL_ALIASES = {
    "python": "python",
    "питон": "python",
    "пайтон": "python",
    "py": "python",
    "python3": "python",
    "sql": "sql",
    "сиквел": "sql",
    "эс кью эл": "sql",
    "postgres": "sql",
    "postgresql": "sql",
    "clickhouse": "sql",
    "pandas": "pandas",
    "пандас": "pandas",
    "numpy": "numpy",
    "нампай": "numpy",
    "sklearn": "sklearn",
    "scikit": "sklearn",
    "scikit learn": "sklearn",
    "сайкит": "sklearn",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "пайторч": "pytorch",
    "tensorflow": "tensorflow",
    "тензорфлоу": "tensorflow",
    "машинное обучение": "ml",
    "machine learning": "ml",
    "ml": "ml",
    "мл": "ml",
    "мл ": "ml",
    "эмель": "ml",
    "эмел": "ml",
    "машинка": "ml",
    "модели": "ml",
    "airflow": "airflow",
    "эйрфлоу": "airflow",
    "аирфлоу": "airflow",
    "spark": "spark",
    "спарк": "spark",
    "kafka": "kafka",
    "кафка": "kafka",
    "etl": "etl",
    "elt": "etl",
    "етл": "etl",
    "итл": "etl",
    "dwh": "dwh",
    "data warehouse": "dwh",
    "дата ворхаус": "dwh",
    "хранилище": "dwh",
    "витрин": "dwh",
    "docker": "docker",
    "докер": "docker",
    "докера": "docker",
    "контейнер": "docker",
    "kubernetes": "kubernetes",
    "кубер": "kubernetes",
    "кубером": "kubernetes",
    "кубернетес": "kubernetes",
    "k8s": "kubernetes",
    "ci/cd": "ci_cd",
    "cicd": "ci_cd",
    "ci cd": "ci_cd",
    "сиай сиди": "ci_cd",
    "пайплайн деплоя": "ci_cd",
    "mlflow": "mlflow",
    "эмелфлоу": "mlflow",
    "dvc": "dvc",
    "monitoring": "monitoring",
    "мониторинг": "monitoring",
    "наблюдаемость": "monitoring",
    "prometheus": "monitoring",
    "grafana": "monitoring",
    "tableau": "tableau",
    "табло": "tableau",
    "power bi": "power_bi",
    "powerbi": "power_bi",
    "пауэр би": "power_bi",
    "би": "power_bi",
    "excel": "excel",
    "эксель": "excel",
    "google sheets": "excel",
    "a/b": "ab_testing",
    "ab тест": "ab_testing",
    "a b тест": "ab_testing",
    "аб тест": "ab_testing",
    "эксперимент": "ab_testing",
    "гипотез": "ab_testing",
    "статист": "statistics",
    "аналитика": "statistics",
    "анализ данных": "statistics",
    "метрик": "statistics",
    "дашборд": "statistics",
    "jira": "jira",
    "джира": "jira",
    "scrum": "scrum",
    "скрам": "scrum",
    "agile": "agile",
    "аджайл": "agile",
    "stakeholder": "stakeholders",
    "стейкхол": "stakeholders",
    "бизнес": "stakeholders",
    "заказчик": "stakeholders",
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
    "имею программировать": "coding_basic",
    "умею программировать": "coding_basic",
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

SKILL_LABELS = {
    "ab_testing": "A/B-тесты",
    "airflow": "Airflow",
    "agile": "Agile",
    "case_solving": "бизнес-кейсы",
    "ci_cd": "CI/CD",
    "coding_basic": "программирование",
    "communication": "коммуникация",
    "docker": "Docker",
    "dwh": "хранилища данных",
    "etl": "ETL",
    "excel": "Excel",
    "jira": "Jira",
    "kafka": "Kafka",
    "kubernetes": "Kubernetes",
    "ml": "ML",
    "mlflow": "MLflow",
    "monitoring": "мониторинг",
    "pandas": "pandas",
    "people_management": "управление людьми",
    "planning": "планирование",
    "power_bi": "Power BI",
    "presentation": "презентация решений",
    "python": "Python",
    "requirements": "сбор требований",
    "risk_management": "управление рисками",
    "scrum": "Scrum",
    "sklearn": "sklearn",
    "spark": "Spark",
    "sql": "SQL",
    "stakeholders": "работа со стейкхолдерами",
    "statistics": "статистика и аналитика",
    "tableau": "Tableau",
}

SALARY_LIMITS = {
    "project_manager": 320000,
    "data_analyst": 240000,
    "data_engineer": 340000,
    "data_scientist": 360000,
    "mlops_engineer": 380000,
}

ROLE_REQUIRED_SKILLS = {
    "project_manager": {"stakeholders", "people_management", "communication", "planning", "risk_management", "scrum", "jira"},
    "data_analyst": {"sql", "statistics", "ab_testing", "power_bi", "tableau", "excel"},
    "data_engineer": {"sql", "python", "airflow", "spark", "kafka", "etl", "dwh"},
    "data_scientist": {"python", "statistics", "ml", "sklearn", "pytorch", "tensorflow", "pandas"},
    "mlops_engineer": {"docker", "kubernetes", "ci_cd", "mlflow", "monitoring", "python"},
}

ROLE_PROJECT_SIGNALS = {
    "project_manager": {"management"},
    "data_analyst": {"analytics"},
    "data_engineer": {"etl"},
    "data_scientist": {"ml_model"},
    "mlops_engineer": {"production_ml"},
}

SCORING_WEIGHTS = {
    "experience": 20,
    "skills": 35,
    "projects": 20,
    "project_role": 8,
    "target_role": 5,
    "education": 6,
    "english": 4,
    "complexity": 2,
    "tie_breaker": 7,
}

QUESTION_BY_SLOT = {
    "candidate_name": "Как вас зовут? Напишите, пожалуйста, фамилию и имя.",
    "target_role": "На какую позицию вы хотите пройти собеседование?",
    "experience_years": "Сколько лет или месяцев релевантной практики можно учитывать? Ответьте числом, например 3.",
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


def normalize_typos(text: str) -> str:
    replacements = {
        "учавств": "участв",
        "учавствовал": "участвовал",
        "учавствовала": "участвовала",
        "имею программировать": "умею программировать",
        "след.": "следующем",
        "след мес": "следующем месяце",
        "сл. месяце": "следующем месяце",
        "вуз": "университет",
        "очно": "офис",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result


def lower_text(tracker: Tracker) -> str:
    return normalize_typos(text_of(tracker).lower().replace("ё", "е"))


def normalize_candidate_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    cleaned = re.sub(r"^(меня зовут|я|это)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned[:120]


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
    raw = str(value).strip().lower()
    normalized = raw.replace("-", " ").replace("_", " ")
    return ROLE_ALIASES.get(raw) or ROLE_ALIASES.get(normalized, "unknown")


def infer_role(text: str) -> str:
    for alias, role in sorted(ROLE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias == "да":
            continue
        normalized_alias = alias.strip()
        if len(normalized_alias) <= 3:
            pattern = r"(?<![\wа-яА-Я])" + re.escape(normalized_alias) + r"(?![\wа-яА-Я])"
            if re.search(pattern, text):
                return role
            continue
        if normalized_alias in text:
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
    if any(phrase in text for phrase in ["без опыта", "нет опыта", "опыта нет", "не было опыта", "давай пропустим", "пропустим", "никогда", "не работал", "не работала", "не занимался", "не занималась", "ноль"]):
        return 0.0
    if "меньше года" in text:
        return 0.5
    if any(phrase in text for phrase in ["полгода", "пол года", "6 месяцев", "шесть месяцев"]):
        return 0.5
    month_match = re.search(r"\b(\d+([\.,]\d+)?)\s*(месяц|месяца|месяцев)\b", text)
    if month_match:
        months = float(month_match.group(1).replace(",", "."))
        if months <= 600:
            return round(months / 12, 1)
    range_match = re.search(r"\b(\d+([\.,]\d+)?)\s*[-–]\s*(\d+([\.,]\d+)?)\b", text)
    if range_match:
        left = float(range_match.group(1).replace(",", "."))
        right = float(range_match.group(3).replace(",", "."))
        if left <= 50 and right <= 50:
            return round((left + right) / 2, 1)
    match = re.search(r"(\d+([\.,]\d+)?)\s*(год|лет|года)", text)
    if match:
        return float(match.group(1).replace(",", "."))
    bare_number = re.fullmatch(r"\s*(\d+([\.,]\d+)?)\s*", text)
    if bare_number:
        number = float(bare_number.group(1).replace(",", "."))
        if number <= 50:
            return number
    return None


def extract_name_from_text(text: str) -> Optional[str]:
    original = re.sub(r"\s+", " ", text.strip())
    if not original:
        return None
    patterns = [
        r"(?:фио|фамилия и имя|имя)\s*[:\-]\s*([А-ЯЁA-Zа-яёa-z]+(?:\s+[А-ЯЁA-Zа-яёa-z]+){1,2})",
        r"(?:меня зовут|я)\s+([А-ЯЁA-Zа-яёa-z]+(?:\s+[А-ЯЁA-Zа-яёa-z]+){1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_candidate_name(match.group(1))
    first_line = text.strip().splitlines()[0] if text.strip() else original
    first_line = re.sub(r"\s+", " ", first_line.strip())
    if len(first_line.split()) in {2, 3, 4} and not any(char.isdigit() for char in first_line):
        lowered = first_line.lower()
        if not any(signal in lowered for signal in ["привет", "хочу", "опыт", "python", "sql", "аналит", "инженер", "менедж"]):
            return normalize_candidate_name(first_line)
    if len(original.split()) in {2, 3, 4} and not any(char.isdigit() for char in original):
        lowered = original.lower()
        if not any(signal in lowered for signal in ["привет", "хочу", "опыт", "python", "sql", "аналит", "инженер", "менедж"]):
            return normalize_candidate_name(original)
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
        "analytics": ["дашборд", "метрик", "bi", "ab", "a/b", "аналит", "поведен", "выручк", "потребител", "маркетплейс"],
        "ml_model": ["модель", "ml", "мл", "эмель", "классификац", "регресс", "прогноз", "рекоменд", "нейрон", "nlp", "cv"],
        "production_ml": ["production", "продакшн", "деплой", "инференс", "serving", "monitoring", "мониторинг", "эксплуатац"],
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
            "деплой",
            "инференс",
            "эмель",
            "мл",
        ]
    )


def is_skip_like(text: str) -> bool:
    return any(phrase in text for phrase in ["не знаю", "незнаю", "не уверен", "пропустим", "давай пропустим", "затрудняюсь"])


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
    clean = re.sub(r"[^\wа-яА-Я]+", " ", raw).strip()
    if clean in {"да", "ага", "угу", "вполне", "норм", "нормально", "спокойно"}:
        return "b1"
    if clean in {"нет", "неа", "никак"}:
        return "none"
    if any(word in raw for word in ["нет", "никак", "не знаю", "незнаю", "не использую", "не читаю"]):
        return "none"
    if any(word in raw for word in ["свобод", "advanced", "fluent", "отлично"]):
        return "c1"
    if any(word in raw for word in ["upper intermediate", "upper", "выше среднего", "уверенный", "очень хорошо", "без проблем", "легко читаю", "хорошо говорю"]):
        return "b2"
    if any(word in raw for word in ["документац", "доку", "док", "intermediate", "средний", "разговорный", "нормально", "вполне", "спокойно", "хорошо", "читаю", "переписываюсь"]):
        return "b1"
    if any(word in raw for word in ["со словарем", "базовый", "начальный", "плохо", "слабо"]):
        return "a2"
    return "unknown"


def normalize_work_format(text: str, value: Any = None) -> str:
    raw = str(value or text).lower()
    if any(word in raw for word in ["remote", "удален", "дистан"]):
        return "remote"
    if any(word in raw for word in ["hybrid", "гибрид"]):
        return "hybrid"
    if any(word in raw for word in ["office", "офис", "очно"]):
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
    if any(word in raw for word in ["недел", "месяц", "скоро", "отрабаты", "отработки", "следующем", "после майских", "три недели"]):
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


def has_education_context(text: str) -> bool:
    return any(
        word in text
        for word in [
            "образован",
            "бакалавр",
            "бакалавриат",
            "магистр",
            "магистрат",
            "университет",
            "институт",
            "вуз",
            "курс",
            "сертифик",
            "computer science",
            "компьютерн",
            "математ",
            "физмат",
        ]
    )


def education_snippet(original_text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", original_text.strip())
    selected = [part.strip() for part in parts if has_education_context(part.lower().replace("ё", "е"))]
    if selected:
        return " ".join(selected)[:500]
    return original_text.strip()[:500]


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
    latest_intent = (tracker.latest_message.get("intent") or {}).get("name")
    skills = infer_skills(text, entities(tracker, "skill"), allow_free_text=requested_slot == "skills") if requested_slot == "skills" or latest_intent in {"provide_skills", "provide_multiple_fields"} or entities(tracker, "skill") else []
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
    english_signal = requested_slot == "english_level" or entities(tracker, "english_level") or "англий" in text or "english" in text or bool(re.search(r"\b[abc][12]\b", text))
    english = normalize_english(text, (entities(tracker, "english_level") or [None])[0]) if english_signal else "unknown"
    if english != "unknown":
        facts["english_level"] = english
    work_signal = requested_slot == "work_format" or entities(tracker, "work_format") or any(word in text for word in ["удален", "remote", "офис", "гибрид", "очно", "дистан"])
    work_format = normalize_work_format(text, (entities(tracker, "work_format") or [None])[0]) if work_signal else "unknown"
    if work_format != "unknown":
        facts["work_format"] = work_format
    availability_signal = requested_slot == "availability" or entities(tracker, "availability") or any(word in text for word in ["готов выйти", "готова выйти", "выйти", "приступить", "отработка"])
    availability = normalize_availability(text, (entities(tracker, "availability") or [None])[0]) if availability_signal else "unknown"
    if availability != "unknown":
        facts["availability"] = availability
    if requested_slot == "salary_expectation_min" and "миллион" in text:
        facts["salary_expectation_min"] = 1000000.0
        facts["salary_expectation_max"] = None
        return facts
    salary_min, salary_max = parse_salary(text, entities(tracker, "salary_amount"))
    if salary_min is not None:
        facts["salary_expectation_min"] = salary_min
        facts["salary_expectation_max"] = salary_max
    if requested_slot == "education_text" or has_education_context(text):
        levels, fields = infer_education(text)
        if levels or fields:
            facts["education_text"] = education_snippet(text_of(tracker))
            facts["education_level"] = levels
            facts["education_field"] = fields
    return facts


def contextual_prompt(requested_slot: Optional[str]) -> str:
    prompts = {
        "candidate_name": "Напишите, пожалуйста, фамилию и имя.",
        "target_role": "Уточните позицию: Project Manager, Data Analyst, Data Engineer, Data Scientist или MLOps Engineer.",
        "experience_years": "Уточните срок релевантной практики: например 0, 6 месяцев, 1.5 или 3 года.",
        "skills": "Назовите несколько навыков, инструментов или сильных сторон, которые важны для этой роли.",
        "project_types": "Опишите один релевантный проект: задача, ваш вклад и результат. Если проектов не было, так и напишите.",
        "project_role": "Уточните вашу роль в проекте: анализировали, разрабатывали, управляли или лидировали?",
        "education_text": "Напишите образование, курсы или профильную подготовку. Если профильного обучения нет, можно так и ответить.",
        "english_level": "Уточните английский: например A2, B1, B2, 'читаю документацию', 'говорю свободно' или 'не использую'.",
        "work_format": "Уточните формат работы: офис, удаленно, гибрид или любой вариант.",
        "salary_expectation_min": "Укажите зарплату числом или диапазоном, например 200к или 200-300 тысяч.",
        "availability": "Уточните срок выхода: сразу, через две недели, в следующем месяце или позже.",
    }
    return prompts.get(requested_slot, "Уточните ответ, пожалуйста.")


def slot_facts_from_text(tracker: Tracker) -> Dict[str, Any]:
    text = lower_text(tracker)
    requested_slot = tracker.get_slot("requested_slot")
    facts = extract_facts(tracker)
    if requested_slot == "candidate_name":
        name = extract_name_from_text(text_of(tracker))
        if name:
            facts["candidate_name"] = name
    if requested_slot == "experience_years" and "experience_years" not in facts:
        years = parse_years(text, entities(tracker, "experience_years"))
        if years is not None:
            facts["experience_years"] = years
    if requested_slot == "english_level" and "english_level" not in facts:
        english = normalize_english(text, (entities(tracker, "english_level") or [None])[0])
        if english != "unknown":
            facts["english_level"] = english
    if requested_slot == "work_format" and "work_format" not in facts:
        work_format = normalize_work_format(text, (entities(tracker, "work_format") or [None])[0])
        if work_format != "unknown":
            facts["work_format"] = work_format
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
    breakdowns: Dict[str, Dict[str, float]] = {}
    for role, weights in ROLE_SKILL_WEIGHTS.items():
        breakdown = {
            "experience": round(min(years, 5.0) / 5.0 * SCORING_WEIGHTS["experience"], 1),
            "skills": 0.0,
            "projects": 0.0,
            "project_role": 0.0,
            "target_role": 0.0,
            "education": 0.0,
            "english": 0.0,
            "complexity": 0.0,
            "tie_breaker": 0.0,
        }
        role_reasons = []
        matched = []
        raw_skill_score = 0.0
        max_skill_score = sum(weights.get(skill, 0) for skill in ROLE_REQUIRED_SKILLS[role]) or 1
        for skill, weight in weights.items():
            if skill in skills:
                raw_skill_score += weight
                matched.append(skill)
        breakdown["skills"] = round(min(raw_skill_score / max_skill_score, 1.0) * SCORING_WEIGHTS["skills"], 1)
        if matched:
            role_reasons.append("релевантные навыки: " + ", ".join(matched[:5]))
        if role == target_role:
            breakdown["target_role"] = SCORING_WEIGHTS["target_role"]
            role_reasons.append("кандидат целится в эту роль")
        if role == "project_manager" and project_role in {"manager", "lead"}:
            breakdown["project_role"] = SCORING_WEIGHTS["project_role"]
            role_reasons.append("есть управленческая роль в проектах")
        if role == "data_analyst" and ("analytics" in projects or project_role == "analyst"):
            breakdown["project_role"] = SCORING_WEIGHTS["project_role"]
            role_reasons.append("есть аналитические проекты или роль аналитика")
        if role == "data_engineer" and ("etl" in projects or "dwh" in skills):
            breakdown["project_role"] = SCORING_WEIGHTS["project_role"]
            role_reasons.append("есть опыт data pipelines или DWH")
        if role == "data_scientist" and "ml_model" in projects:
            breakdown["project_role"] = SCORING_WEIGHTS["project_role"]
            role_reasons.append("есть опыт ML-моделей")
        if role == "mlops_engineer" and "production_ml" in projects:
            breakdown["project_role"] = SCORING_WEIGHTS["project_role"]
            role_reasons.append("есть production/MLOps опыт")
        if ROLE_PROJECT_SIGNALS[role] & projects:
            breakdown["projects"] = SCORING_WEIGHTS["projects"]
        elif projects and "no_relevant_projects" not in projects:
            breakdown["projects"] = round(SCORING_WEIGHTS["projects"] * 0.45, 1)
        if complexity == "high":
            breakdown["complexity"] = SCORING_WEIGHTS["complexity"]
            role_reasons.append("проекты высокой сложности")
        elif complexity == "medium":
            breakdown["complexity"] = round(SCORING_WEIGHTS["complexity"] * 0.5, 1)
        elif complexity == "low":
            breakdown["complexity"] = -2.0
        if "technical" in education_fields and role in {"data_engineer", "data_scientist", "mlops_engineer"}:
            breakdown["education"] = max(breakdown["education"], SCORING_WEIGHTS["education"])
        if "data" in education_fields and role in {"data_analyst", "data_scientist"}:
            breakdown["education"] = max(breakdown["education"], SCORING_WEIGHTS["education"])
        if "business" in education_fields and role == "project_manager":
            breakdown["education"] = max(breakdown["education"], SCORING_WEIGHTS["education"])
        if english in {"b2", "c1", "c2"}:
            breakdown["english"] = SCORING_WEIGHTS["english"]
        elif english == "b1":
            breakdown["english"] = round(SCORING_WEIGHTS["english"] * 0.5, 1)
        elif english in {"none", "a1"}:
            breakdown["english"] = -3.0
        if tie_text:
            tie_boosts = {
                "project_manager": ["управ", "команд", "коммуникац", "stakeholder"],
                "data_analyst": ["bi", "аналит", "метрик", "дашборд", "гипотез"],
                "data_engineer": ["пайплайн", "pipeline", "etl", "данных", "инженер"],
                "data_scientist": ["ml", "мл", "эмель", "модель", "исслед", "эксперимент"],
                "mlops_engineer": ["production", "инфраструкт", "эксплуатац", "деплой", "kubernetes", "кубер"],
            }
            if any(word in tie_text for word in tie_boosts[role]):
                breakdown["tie_breaker"] = SCORING_WEIGHTS["tie_breaker"]
                role_reasons.append("tie-breaker ответ усилил роль")
        score = sum(breakdown.values())
        scores[role] = max(0, min(round(score, 1), 100))
        breakdowns[role] = breakdown
        reasons[role] = role_reasons or ["профиль частично пересекается с ролью"]
    ranking = sorted(
        [{"role": role, "label": ROLE_LABELS[role], "score": score, "reasons": reasons[role], "score_breakdown": breakdowns[role]} for role, score in scores.items()],
        key=lambda item: item["score"],
        reverse=True,
    )
    top = ranking[0]
    second = ranking[1]
    if top["score"] >= 70:
        decision = "fit"
    elif top["score"] >= 50:
        decision = "borderline"
    else:
        decision = "reject"
    tie_question = None
    if top["score"] >= 50 and abs(top["score"] - second["score"]) <= 7 and not tie_answer:
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
    if top_score < 50:
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
    missing = sorted(ROLE_REQUIRED_SKILLS[top_role] - skills)[:3]
    if missing:
        risks.append("не хватает ключевых сигналов роли: " + ", ".join(missing))
    return risks or ["критичных рисков не обнаружено"]


def build_candidate_summary(slots: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_name": slots.get("candidate_name"),
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
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = export_dir / f"{safe_sender}_{stamp}.json"
    csv_path = export_dir / f"{safe_sender}_{stamp}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["candidate_summary"]
    row = {
        "created_at": report["created_at"],
        "candidate_name": summary.get("candidate_name"),
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


def human_reasons(result: Dict[str, Any]) -> List[str]:
    reasons = result["ranking"][0].get("reasons") or []
    cleaned = []
    replacements = {
        "релевантные навыки": "релевантные навыки",
        "кандидат целится в эту роль": "вы рассматриваете это направление",
        "есть production/MLOps опыт": "есть опыт с production/MLOps-задачами",
        "есть опыт ML-моделей": "есть опыт с ML-моделями",
        "есть опыт data pipelines или DWH": "есть опыт с пайплайнами данных или хранилищами",
        "есть аналитические проекты или роль аналитика": "есть аналитический опыт",
        "есть управленческая роль в проектах": "есть управленческий опыт",
        "проекты высокой сложности": "есть признаки сложных проектов",
        "профиль частично пересекается с ролью": "часть опыта пересекается с ролью",
    }
    for reason in reasons:
        item = reason
        for source, target in replacements.items():
            item = item.replace(source, target)
        if item.startswith("релевантные навыки:"):
            raw_skills = [skill.strip() for skill in item.split(":", 1)[1].split(",")]
            labels = [SKILL_LABELS.get(skill, skill) for skill in raw_skills]
            item = "релевантные навыки: " + ", ".join(labels)
        cleaned.append(item)
    return cleaned[:3] or ["в ответах есть несколько релевантных сигналов для этой роли"]


def human_follow_up_questions(result: Dict[str, Any]) -> List[str]:
    questions = []
    for risk in result.get("risk_flags") or []:
        if risk == "критичных рисков не обнаружено":
            continue
        if risk.startswith("не хватает ключевых сигналов роли:"):
            missing = ", ".join(SKILL_LABELS.get(skill.strip(), skill.strip()) for skill in risk.split(":", 1)[1].split(","))
            questions.append(f"Можете подробнее рассказать про опыт с {missing}?")
        elif risk == "желаемая роль отличается от рекомендованной":
            questions.append("Какая роль вам все-таки ближе: выбранная изначально или та, к которой оказался ближе опыт?")
        elif risk == "зарплатные ожидания выше типичного диапазона роли":
            questions.append("Насколько гибкая ваша зарплатная вилка?")
        elif risk == "английский может ограничить работу с документацией и международной командой":
            questions.append("Какой уровень английского можно подтвердить на интервью?")
        elif risk == "кандидат доступен не скоро":
            questions.append("Можно ли будет обсудить более раннюю дату выхода?")
        elif risk == "нет признаков проектов промышленной сложности":
            questions.append("Были ли проекты с production-нагрузкой, реальными пользователями или бизнес-метриками?")
        elif risk == "мало релевантного опыта":
            questions.append("Есть ли стажировки, учебные или pet-проекты, которые стоит учесть?")
        elif risk == "низкое соответствие всем пяти ролям":
            questions.append("Есть ли еще релевантный опыт, который мы не обсудили?")
    return questions[:3]


def final_message(result: Dict[str, Any], slots: Dict[str, Any]) -> str:
    recommended = ROLE_LABELS[result["recommended_role"]]
    alternatives = [item["label"] for item in result["ranking"][1:3]]
    reasons = human_reasons(result)
    name = slots.get("candidate_name")
    greeting = f"{name}, спасибо, интервью завершено." if name else "Спасибо, интервью завершено."
    if result["decision_status"] == "fit":
        status = f"По вашим ответам лучше всего подходит направление {recommended}."
        next_step_text = "Следующий шаг: передать профиль на техническое интервью."
    elif result["decision_status"] == "borderline":
        status = f"По вашим ответам профиль ближе всего к направлению {recommended}, но я бы дополнительно сверил детали с рекрутером."
        next_step_text = "Следующий шаг: короткий созвон с рекрутером, чтобы уточнить опыт и ожидания."
    else:
        status = f"По текущим ответам сильного совпадения с открытыми ролями пока не видно. Ближайшее направление: {recommended}."
        next_step_text = "Следующий шаг: рекрутер сможет вернуться к профилю, если появится более подходящая вакансия."
    parts = [
        greeting,
        "",
        "Итог:",
        f"- {status}",
        f"- Также можно рассмотреть: {', '.join(alternatives)}.",
        "",
        "Почему:",
    ]
    parts.extend(f"- {reason}." for reason in reasons)
    parts.extend(["", next_step_text])
    return "\n".join(parts)


def finalize(dispatcher: CollectingDispatcher, tracker: Tracker, slots: Dict[str, Any], result: Dict[str, Any]) -> List[SlotSet]:
    report = build_recruiter_report(slots, result)
    json_path, csv_path = export_report(tracker.sender_id, report)
    dispatcher.utter_message(text=final_message(result, slots))
    return [
        SlotSet("candidate_summary", report["candidate_summary"]),
        SlotSet("recruiter_report", report),
        SlotSet("role_ranking", result["ranking"]),
        SlotSet("risk_flags", result["risk_flags"]),
        SlotSet("decision_status", result["decision_status"]),
        SlotSet("recommended_role", result["recommended_role"]),
        SlotSet("tie_breaker_question", None),
        SlotSet("follow_up_questions", []),
        SlotSet("export_path_json", json_path),
        SlotSet("export_path_csv", csv_path),
    ]


class ActionContextualFallback(Action):
    def name(self) -> Text:
        return "action_contextual_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        facts = slot_facts_from_text(tracker)
        requested_slot = tracker.get_slot("requested_slot")
        events: List[SlotSet] = []
        for slot_name, value in facts.items():
            events.append(SlotSet(slot_name, value))
        if events:
            return events
        dispatcher.utter_message(text=contextual_prompt(requested_slot))
        return []


class ValidateInterviewForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_interview_form"

    async def extract_candidate_name(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if tracker.get_slot("requested_slot") != "candidate_name":
            return {}
        facts = extract_facts(tracker)
        name = extract_name_from_text(text_of(tracker))
        if name:
            facts["candidate_name"] = name
        return facts

    def validate_candidate_name(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        name = normalize_candidate_name(str(slot_value or ""))
        if len(name.split()) < 2 or len(name) < 5:
            dispatcher.utter_message(text="Напишите, пожалуйста, фамилию и имя, чтобы рекрутер видел, чей это отклик.")
            return {"candidate_name": None}
        return {"candidate_name": name}

    async def extract_target_role(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        text = lower_text(tracker)
        if tracker.get_slot("requested_slot") != "target_role" and not entities(tracker, "target_role"):
            role = infer_role(lower_text(tracker))
            return {"target_role": role} if role != "unknown" else {}
        facts = extract_facts(tracker)
        if not facts.get("target_role") and any(token in text for token in ["не знаю", "подбери", "не определился", "любая", "любой"]):
            facts["target_role"] = "unknown"
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
        latest_intent = (tracker.latest_message.get("intent") or {}).get("name")
        if tracker.get_slot("requested_slot") != "skills" and latest_intent not in {"provide_skills", "provide_multiple_fields"}:
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
        text = lower_text(tracker)
        if is_skip_like(text):
            return {"english_level": "unknown"}
        english = normalize_english(text, (entities(tracker, "english_level") or [None])[0])
        if english != "unknown":
            return {"english_level": english}
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
        text = lower_text(tracker)
        if not slot_value or slot_value == "unknown":
            if any(token in text for token in ["не знаю", "подбери", "не определился", "любая", "любой"]):
                return {"target_role": "unknown"}
            dispatcher.utter_message(text=contextual_prompt("target_role"))
            return {"target_role": None}
        return {"target_role": slot_value}

    def validate_experience_years(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            if not is_out_of_scope_text(lower_text(tracker)):
                dispatcher.utter_message(text="Сейчас нужен именно срок практики. Напишите число лет или месяцев, например: 3, 1.5 или 6 месяцев. Если релевантного опыта нет, можно так и написать.")
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
        if slot_value is None:
            dispatcher.utter_message(text=contextual_prompt("english_level"))
            return {"english_level": None}
        return {"english_level": slot_value or "unknown"}

    def validate_work_format(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text=contextual_prompt("work_format"))
            return {"work_format": None}
        return {"work_format": slot_value or "unknown"}

    def validate_salary_expectation_min(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text="Укажите зарплатные ожидания числом или диапазоном.")
            return {"salary_expectation_min": None}
        return {"salary_expectation_min": float(slot_value)}

    def validate_availability(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text=contextual_prompt("availability"))
            return {"availability": None}
        return {"availability": slot_value or "unknown"}


class ActionRankCandidate(Action):
    def name(self) -> Text:
        return "action_rank_candidate"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slots = tracker.current_slot_values()
        result = score_candidate(slots)
        if result["tie_breaker_question"]:
            dispatcher.utter_message(text=f"Хочу точнее понять ваш профиль. {result['tie_breaker_question']}")
            return [
                SlotSet("role_ranking", result["ranking"]),
                SlotSet("risk_flags", result["risk_flags"]),
                SlotSet("decision_status", result["decision_status"]),
                SlotSet("recommended_role", result["recommended_role"]),
                SlotSet("tie_breaker_question", result["tie_breaker_question"]),
            ]
        follow_ups = human_follow_up_questions(result)
        if follow_ups:
            dispatcher.utter_message(text="Подскажите еще: " + " ".join(follow_ups))
            return [
                SlotSet("role_ranking", result["ranking"]),
                SlotSet("risk_flags", result["risk_flags"]),
                SlotSet("decision_status", result["decision_status"]),
                SlotSet("recommended_role", result["recommended_role"]),
                SlotSet("follow_up_questions", follow_ups),
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


class ActionApplyFollowUp(Action):
    def name(self) -> Text:
        return "action_apply_follow_up"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not tracker.get_slot("follow_up_questions"):
            dispatcher.utter_message(text="Сейчас нет открытого уточнения. Можем продолжить интервью.")
            return []
        text = lower_text(tracker)
        slots = tracker.current_slot_values()
        updated_slots = dict(slots)
        skills = infer_skills(text, entities(tracker, "skill"), allow_free_text=False)
        projects = infer_projects(text, entities(tracker, "project_type")) if has_project_context(text) else []
        salary_min, salary_max = parse_salary(text, entities(tracker, "salary_amount"))
        english = normalize_english(text, (entities(tracker, "english_level") or [None])[0])
        work_format = normalize_work_format(text, (entities(tracker, "work_format") or [None])[0])
        availability = normalize_availability(text, (entities(tracker, "availability") or [None])[0])
        if skills:
            updated_slots["skills"] = unique((slots.get("skills") or []) + skills)
        if projects:
            updated_slots["project_types"] = unique((slots.get("project_types") or []) + projects)
            updated_slots["project_complexity"] = infer_complexity(text)
        if salary_min is not None:
            updated_slots["salary_expectation_min"] = salary_min
            updated_slots["salary_expectation_max"] = salary_max
        if english != "unknown":
            updated_slots["english_level"] = english
        if work_format != "unknown":
            updated_slots["work_format"] = work_format
        if availability != "unknown":
            updated_slots["availability"] = availability
        result = score_candidate(updated_slots)
        events = finalize(dispatcher, tracker, updated_slots, result)
        events.append(SlotSet("follow_up_answer", text_of(tracker)))
        if skills:
            events.append(SlotSet("skills", updated_slots["skills"]))
        if projects:
            events.append(SlotSet("project_types", updated_slots["project_types"]))
            events.append(SlotSet("project_complexity", updated_slots["project_complexity"]))
        if salary_min is not None:
            events.append(SlotSet("salary_expectation_min", salary_min))
            events.append(SlotSet("salary_expectation_max", salary_max))
        if english != "unknown":
            events.append(SlotSet("english_level", english))
        if work_format != "unknown":
            events.append(SlotSet("work_format", work_format))
        if availability != "unknown":
            events.append(SlotSet("availability", availability))
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
            dispatcher.utter_message(text=tie_question)
            return []
        follow_ups = tracker.get_slot("follow_up_questions") or []
        if follow_ups:
            dispatcher.utter_message(text="Ответьте, пожалуйста: " + " ".join(follow_ups))
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
