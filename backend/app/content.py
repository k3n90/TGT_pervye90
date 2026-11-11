"""Тексты треков. Пункты наблюдаемые: их можно отметить в конце смены."""

from __future__ import annotations

QUESTIONS = [
    ("q1", "Понимаю, что от меня ждут"),
    ("q2", "Справляюсь"),
    ("q3", "Хочу здесь остаться"),
]

ANSWER_LABELS = {"yes": "Да", "mid": "Средне", "no": "Нет"}

STAGE_LABELS = {
    "waiting": "Ждёт выхода",
    "first_week": "Первая неделя",
    "until_30": "До 30 дней",
    "until_end": "До конца испытания",
    "closed": "Испытание закрыто",
    "dismissed": "Уволен на испытании",
}

ADMISSION_LABELS = {
    "none": "Допуска нет",
    "caveat": "Допуск с оговоркой",
    "yes": "Работает сам",
}

DAY30_LABELS = {
    "independent": "Работает сам",
    "still_with_mentor": "Ещё с наставником",
    "role_unfit": "Роль не подходит",
}

DECISION_LABELS = {
    "confirm": "Подтверждаем",
    "separate": "Расстаёмся",
    "transfer": "Переводим внутри точки",
}

RESOLUTION_LABELS = {
    "fixed": "Поправили условие",
    "recheck": "Повторная проверка",
    "separation": "Запустили расставание",
    "auto": "Условие снято",
}

ROLE_LABELS = {
    "hr": "Кадры",
    "mentor": "Наставник",
    "manager": "Руководитель",
    "director": "Директор функции",
}

HIRE_SOURCES = [
    "Рекомендация сотрудника",
    "Работный сайт",
    "Пришёл сам",
    "Объявление у входа",
]

PROBATION_OPTIONS = [
    {"days": 90, "label": "90 дней"},
    {"days": 60, "label": "60 дней"},
    {"days": 30, "label": "30 дней"},
    {"days": 0, "label": "Без испытания"},
]

# include: always | position | shared_warehouse
# critical items with include always/position: не больше пяти на трек.

TRACKS: list[dict] = [
    {
        "code": "warehouse",
        "name": "Склад",
        "department": "Склад",
        "location": "Склад, пр-т Дзержинского, 90",
        "independence_day": 14,
        "positions": [
            ("picker", "Комплектовщик"),
            ("storekeeper", "Кладовщик"),
        ],
        "items": [
            ("wh_pass", 1, False, "always", None, "Получил пропуск и усвоил, где раздевалка и выход на рампу."),
            ("wh_map", 1, True, "always", None, "Усвоил на схеме склада зоны розницы, опта и отгрузки на маркетплейс."),
            ("wh_ban", 1, True, "always", None, "Самостоятельно назвал, что нельзя отгружать: чужой размер, вскрытая упаковка, позиция без скана."),
            ("wh_break", 1, False, "always", None, "Самостоятельно назвал, кто подменяет его на перерыве."),
            (
                "wh_ragex",
                1,
                True,
                "shared_warehouse",
                None,
                "Технику RAGEX без целого гарантийного стикера не отгрузил, бой отложил отдельно.",
            ),
            ("wh_simple", 7, True, "always", None, "Сам собрал простой розничный заказ из трёх позиций без пересорта размера."),
            ("wh_b2b", 7, True, "always", None, "Отличил заказ юрлица от розницы и не положил его в розничный короб."),
            ("wh_short", 7, False, "always", None, "При нехватке на адресе позвал старшего, а не закрыл позицию «примерно»."),
            (
                "wh_intake",
                7,
                False,
                "position",
                "storekeeper",
                "Принял поставку, сверил количество и отложил брак отдельно от годного.",
            ),
            (
                "wh_wave",
                14,
                True,
                "always",
                None,
                "Отработал обычную волну без критических ошибок: чужой размер, пересорт командного заказа, повреждённая техника.",
            ),
            ("wh_scan", 14, False, "always", None, "На десяти позициях подряд скан совпал с местом хранения."),
        ],
    },
    {
        "code": "retail",
        "name": "Розница GOODSPORTS",
        "department": "Розница GOODSPORTS",
        "location": "Зал GOODSPORTS, пом. 411",
        "independence_day": 14,
        "positions": [
            ("seller", "Продавец зала"),
            ("shift_lead", "Старший смены"),
        ],
        "items": [
            (
                "rt_graph",
                1,
                False,
                "always",
                None,
                "Назвал свой график на две недели, включая вечер и воскресенье. Зал работает 9:00–21:00 без выходных.",
            ),
            (
                "rt_pvz",
                1,
                True,
                "always",
                None,
                "Показал, где касса и где ПВЗ опта, и когда покупателя-юрлицо вести в пом. 417, а не обслуживать как розницу.",
            ),
            (
                "rt_size",
                1,
                True,
                "always",
                None,
                "Разложил размерную логику: футбол, баскетбол, и т.д.",
            ),
            ("rt_sale", 7, True, "always", None, "Сам провёл типовую продажу: размер, наличие, чек."),
            (
                "rt_cards",
                7,
                False,
                "always",
                None,
                "Назвал карты рассрочки, которые реально есть на кассе, и не добавил лишних.",
            ),
            (
                "rt_return",
                7,
                True,
                "always",
                None,
                "Оформил типовой возврат и/или на нестандартном случае позвал старшего, а не решал исход сам.",
            ),
            (
                "rt_shift",
                7,
                False,
                "position",
                "shift_lead",
                "Открыл смену по короткому списку старшего: касса, зал, кто на подмене.",
            ),
            (
                "rt_alone",
                14,
                True,
                "always",
                None,
                "Провёл типовую продажу и типовой возврат сам, старший только сверил итог чека.",
            ),
            (
                "rt_peak",
                14,
                False,
                "always",
                None,
                "В первую неделю не остался один на вечер пятницы и на субботу.",
            ),
        ],
    },
    {
        "code": "wholesale",
        "name": "Оптовые продажи",
        "department": "Оптовые продажи",
        "location": "ПВЗ опт, пом. 417",
        "independence_day": 30,
        "positions": [("wholesale_manager", "Менеджер опта")],
        "items": [
            ("ws_discount", 1, True, "always", None, "Сказал, кто согласует скидку, и не пообещал её клиенту сам."),
            (
                "ws_path",
                1,
                False,
                "always",
                None,
                "Показал путь заказа: заявка, счёт юрлицу, наличие, выдача в ПВЗ пом. 417.",
            ),
            (
                "ws_answer",
                7,
                True,
                "always",
                None,
                "Собрал ответ по типовому заказу: наличие, срок 1–3 рабочих дня, самовывоз, Белпочта или Европочта.",
            ),
            ("ws_stock", 7, True, "always", None, "Не назвал наличие по памяти и записал, у кого уточнил."),
            ("ws_invoice", 14, False, "always", None, "Подготовил счёт по шаблону и сверил реквизиты с руководителем до отправки."),
            ("ws_full", 30, True, "always", None, "Сам довёл типовой заказ юрлица до выдачи в ПВЗ."),
            ("ws_gap", 30, False, "always", None, "Расхождение наличия записал, а не оставил в чате «примерно есть»."),
        ],
    },
    {
        "code": "ragex",
        "name": "RAGEX и маркетплейсы",
        "department": "RAGEX и маркетплейсы",
        "location": "RAGEX, пом. 427",
        "independence_day": 30,
        "positions": [("ragex_specialist", "Специалист RAGEX и маркетплейсов")],
        "items": [
            (
                "rx_warranty",
                1,
                True,
                "always",
                None,
                "Не назвал срок гарантии, пока не ясен тип товара: 12 месяцев или 24 на отдельные виды.",
            ),
            ("rx_return", 1, True, "always", None, "Назвал возврат 30 дней и кому передаёт спорный брак."),
            ("rx_stock", 7, True, "always", None, "Показал, где правится остаток, и не подтвердил наличие покупателю по памяти."),
            ("rx_sla", 7, False, "always", None, "Назвал срок ответа покупателю маркетплейса, принятый в отделе."),
            (
                "rx_channel",
                14,
                True,
                "always",
                None,
                "Отличил возврат маркетплейса от возврата в зале GOODSPORTS и не смешал сценарии.",
            ),
            (
                "rx_close",
                30,
                True,
                "always",
                None,
                "Сам закрыл типовой вопрос по наличию и гарантии без выдуманного остатка.",
            ),
        ],
    },
    {
        "code": "office",
        "name": "Офис",
        "department": "Офис",
        "location": "Офис, пом. 427",
        "independence_day": 30,
        "positions": [("office_specialist", "Специалист офиса")],
        "items": [
            (
                "of_access",
                1,
                True,
                "always",
                None,
                "Открыты доступы, которые положены должности: почта и Битрикс. 1С — если он есть в задачах этой роли.",
            ),
            ("of_tasks", 1, False, "always", None, "Назвал, кто ставит задачи первые две недели и в каком часе можно задать вопрос."),
            (
                "of_one",
                14,
                False,
                "always",
                None,
                "Закрыл одну типовую задачу своей должности, руководитель поправил не больше одного раза.",
            ),
            ("of_own", 30, True, "always", None, "Закрывает типовую задачу без сопровождения."),
        ],
    },
]

# username, full_name, role, track or None, title, department codes
USERS = [
    ("olga", "Ольга Сеницкая", "hr", None, "Кадровик", []),
    ("pavel", "Павел Остриков", "mentor", "warehouse", "Наставник склада", ["warehouse"]),
    ("irina", "Ирина Лапицкая", "mentor", "retail", "Наставник зала", ["retail"]),
    ("denis", "Денис Корбут", "manager", "warehouse", "Руководитель склада", ["warehouse"]),
    ("marina", "Марина Ельская", "manager", "retail", "Управляющая розницей", ["retail"]),
    ("oleg", "Олег Бриль", "director", "warehouse", "Директор складской логистики", ["warehouse"]),
    ("svetlana", "Светлана Дубовик", "director", "retail", "Директор розницы", ["retail"]),
    ("andrey", "Андрей Пашкевич", "director", "wholesale", "Директор продаж", ["wholesale", "ragex"]),
    ("natalia", "Наталья Ким", "mentor", "wholesale", "Наставник опта", ["wholesale"]),
    ("viktor", "Виктор Савицкий", "manager", "wholesale", "Руководитель опта", ["wholesale"]),
    ("kirill", "Кирилл Дорофеев", "mentor", "ragex", "Наставник RAGEX", ["ragex"]),
    ("roman", "Роман Бельский", "manager", "ragex", "Руководитель RAGEX", ["ragex"]),
    ("elena", "Елена Гришкевич", "mentor", "office", "Наставник офиса", ["office"]),
    ("tatiana", "Татьяна Окулич", "manager", "office", "Руководитель офиса", ["office"]),
]

BASELINE_PLAN = {
    # hires, leavers, short (<90), under30, long
    "warehouse": (48, 24, 8, 3, 16),
    "retail": (36, 18, 6, 3, 12),
    "wholesale": (16, 8, 3, 1, 5),
    "ragex": (10, 5, 2, 1, 3),
    "office": (10, 5, 1, 0, 4),
}


def critical_always_count(track: dict) -> int:
    return sum(
        1
        for item in track["items"]
        if item[2] and item[3] in ("always", "position")
    )


def assert_track_limits() -> None:
    for track in TRACKS:
        count = critical_always_count(track)
        if count > 5:
            raise RuntimeError(f"В треке {track['code']} {count} критических пунктов при лимите 5")
