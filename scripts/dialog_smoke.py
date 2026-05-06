import json
import sys
import time
import urllib.request
import uuid


BASE = "http://localhost:5005"
OUTPUT = "dialog_smoke_output.jsonl"


def post_json(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw or "[]")


def run(name, messages):
    sender = "smoke_" + uuid.uuid4().hex[:8]
    append_event({"scenario": name, "event": "start", "sender": sender})
    for message in messages:
        try:
            responses = post_json("/webhooks/rest/webhook", {"sender": sender, "message": message})
        except Exception as error:
            append_event({"scenario": name, "user": message, "error": repr(error)})
            break
        if not responses:
            append_event({"scenario": name, "user": message, "bot": []})
        else:
            append_event({"scenario": name, "user": message, "bot": responses})
        time.sleep(0.15)


def append_event(event):
    with open(OUTPUT, "a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


SCENARIOS = {
    "info_and_start": [
        "Привет что ты умеешь?",
        "На какие вакансии можно откликнуться?",
        "Хочу собеседоваться на проджект менеджера",
        "Иван Петров",
    ],
    "mlops_medical_candidate": [
        "Привет что ты умеешь?",
        "Как податься на MLOps?",
        "Алексей Смирнов",
        "6-7",
        "Работал над ML проектом в сфере медицины, выявлял рак у детей",
        "Разработчик, но принимал участие в тестировании",
        "Окончил ВУЗ по математической специальности",
        "Вполне",
        "Незнаю",
        "ДА",
        "Нет",
        "Гибрид 2 дня в офисе",
        "200к",
        "Завтра",
    ],
    "data_analyst_typos": [
        "Привет, хочу устроиться на работу",
        "Мария Кузнецова",
        "Дата аналитик",
        "2 года",
        "аналитика, управление, использую различные инструменты и имею программировать",
        "Анализировал поведение клиентов на маркетплейсе, увеличил выручку на 5%",
        "Учавствовал в редизайне системы доставки как аналитик, анализировал поведение потребителей в разных сервисах",
        "Да, закончил бакалавриат недавно по компьютерным наукам",
        "Вполне комфортно",
        "Гибрид или очно",
        "200-300 тысяч",
        "В след. месяце",
    ],
    "pm_conversational_skills": [
        "хочу пройти собес на проджа",
        "Дмитрий Орлов",
        "4 года",
        "А какие навыки есть у проджект менеджера?",
        "Я умею управлять людьми, немножко кодить, у меня хорошие soft skills, побеждал в кейс-чемпионатах",
        "вел команду из 5 человек, планировал сроки, общался с бизнесом",
        "я был лидом и менеджером",
        "вышка менеджмент плюс курсы project management",
        "английский средний, читаю доку",
        "гибрид норм",
        "хочу 250к",
        "могу через две недели",
    ],
    "data_engineer_informal": [
        "привет",
        "хочу на дата инженера",
        "Никита Соколов",
        "примерно 3 года коммерции",
        "питон sql airflow spark kafka, немного докера",
        "пилил пайплайны и витрины, данные гоняли по расписанию",
        "больше разработчик",
        "техническая вышка",
        "b1",
        "удаленка онли",
        "по деньгам 280к",
        "могу хоть завтра",
    ],
    "illogical_interruptions": [
        "хочу податься на вакансию",
        "Анна Морозова",
        "не знаю",
        "какая сегодня погода?",
        "повтори вопрос",
        "давай пропустим",
        "я вообще бариста, но хочу в ML",
        "умею продавать кофе и общаться",
        "проектов нет",
        "никакая роль",
        "образования нет",
        "английского нет",
        "любой формат",
        "хочу миллион",
        "через три месяца",
    ],
    "change_answer": [
        "начать интервью",
        "Екатерина Волкова",
        "Data Scientist",
        "2 года",
        "python sql ml sklearn",
        "делал учебную модель классификации текстов",
        "разработчик",
        "курсы data science",
        "a2",
        "удаленно",
        "180к",
        "готов сразу",
        "измени зарплату на 240к",
        "что дальше?",
    ],
}


if __name__ == "__main__":
    open(OUTPUT, "w", encoding="utf-8").close()
    names = sys.argv[1:] or list(SCENARIOS)
    for scenario_name in names:
        scenario_messages = SCENARIOS[scenario_name]
        run(scenario_name, scenario_messages)
