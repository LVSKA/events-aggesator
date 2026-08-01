# events-aggregator — план и архитектура

Backend-сервис на Django + DRF, интегрирующийся с внешним Events Provider API.
Хранит события и билеты у себя в PostgreSQL, синхронизируется с внешним API фоново
через Celery (broker — Postgres, без Redis).

## 1. Структура проекта

```
events-aggregator/
├── src/
│   ├── core/                      # настройки django, celery app, urls
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── prod.py
│   │   ├── celery.py
│   │   ├── urls.py
│   │   ├── asgi.py / wsgi.py
│   │
│   ├── events_provider/           # клиент внешнего API — ничего кроме HTTP-обёртки
│   │   ├── client.py              # EventsProviderClient
│   │   ├── paginator.py           # EventsPaginator
│   │   ├── exceptions.py
│   │   ├── schemas.py             # dataclasses/pydantic для ответов внешнего API
│   │   └── tests/
│   │       ├── test_client.py
│   │       └── test_paginator.py
│   │
│   ├── events/                    # django app: события и площадки
│   │   ├── models.py              # Event, Place
│   │   ├── serializers.py         # только сериализация, без бизнес-логики
│   │   ├── views.py               # DRF ViewSet/APIView, дергают logic.py
│   │   ├── logic.py                # бизнес-логика (список, детали, места)
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── tickets/                   # django app: регистрации
│   │   ├── models.py              # Ticket
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── logic.py                # CreateTicketUsecase / CancelTicketUsecase
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── sync/                      # django app: фоновая синхронизация
│   │   ├── models.py              # SyncMetadata (last_sync_time, last_changed_at, status)
│   │   ├── tasks.py                # celery task synchronize_events
│   │   ├── logic.py                # SyncEventsUsecase — использует EventsPaginator
│   │   ├── views.py                # POST /api/sync/trigger
│   │   ├── urls.py
│   │   └── tests/
│   │
│   └── healthcheck/
│       ├── views.py                # GET /api/health
│       └── urls.py
│
├── .github/workflows/ci.yml
├── Dockerfile
├── run.sh
├── pyproject.toml                 # uv + ruff config
├── manage.py
└── README.md
```

Разбиение по django-приложениям идёт по предметной области (events / tickets / sync),
а не по техническому слою — это стандартная практика для Django и упрощает
самостоятельные деплои по фичам.

## 2. Модели БД

**events.Place**
- id (UUID, из внешнего API)
- name, city, address
- seats_pattern
- changed_at, created_at (из внешнего API — для дебага рассинхрона)

**events.Event**
- id (UUID, из внешнего API — не генерируем свой)
- name
- place (FK -> Place)
- event_time, registration_deadline
- status (choices: new, published, ...)
- number_of_visitors
- changed_at, created_at, status_changed_at
- индекс по event_time (для date_from фильтра) и по changed_at (для инкрементальной синхронизации)

**tickets.Ticket**
- ticket_id (UUID, из внешнего API)
- event (FK -> Event)
- first_name, last_name, email
- seat
- created_at
- cancelled_at (nullable) — не удаляем строку при отмене, помечаем

**sync.SyncMetadata**
- одна строка (или per-source), хранит last_sync_time, last_changed_at, sync_status (idle/running/failed), last_error

## 3. Клиент внешнего API (events_provider/client.py)

```python
class EventsProviderClient:
    def __init__(self, base_url: str, api_key: str, session: httpx.Client | None = None):
        ...

    def get_events(self, changed_at: str, cursor: str | None = None) -> EventsPage:
        ...

    def get_seats(self, event_id: str) -> list[str]:
        ...

    def register(self, event_id: str, first_name: str, last_name: str, email: str, seat: str) -> str:
        ...

    def unregister(self, event_id: str, ticket_id: str) -> None:
        ...
```

Требования из рекомендаций, которые тут закладываем:
- весь HTTP-код к events-provider — только здесь, больше нигде в проекте
- все URL с trailing slash
- обработка кривого 500 (неопубликованное событие при запросе seats) — превращаем
  в понятное исключение `EventNotPublished`, а не пробрасываем HTML наружу
- `register`/`unregister` пробрасывают понятные исключения (`SeatAlreadyTaken`,
  `EventNotFound`, `AuthError`) вместо сырых HTTP-ошибок
- минимум classmethod/staticmethod — конфигурация (base_url, api_key, http-клиент)
  передаётся через `__init__`, а не через classmethod-конструкторы

Это Protocol-совместимый класс — в usecases он будет использоваться через
`typing.Protocol`, чтобы бизнес-логика не зависела от конкретной реализации
(упрощает моки в тестах).

## 4. EventsPaginator (events_provider/paginator.py)

```python
class EventsPaginator:
    def __init__(self, client: EventsProviderClient, changed_at: str):
        self._client = client
        self._changed_at = changed_at

    def __iter__(self):
        cursor = None
        while True:
            page = self._client.get_events(self._changed_at, cursor=cursor)
            yield from page.results
            if page.next_cursor is None:
                return
            cursor = page.next_cursor
```

Используется как:
```python
for event in EventsPaginator(client, changed_at="2000-01-01"):
    usecase.save_event(event)
```

Курсор парсится из `next` (полного URL) один раз внутри клиента/пагинатора —
наружу отдаём только сам курсор, а не URL, чтобы верхний уровень не знал деталей
формата пагинации внешнего сервиса.

## 5. Бизнес-логика (logic.py в каждом app)

Правило: сериалайзеры DRF ничего не знают ни о клиенте, ни о бизнес-правилах,
только валидация формы данных. Все обращения к БД и к EventsProviderClient — в
`logic.py`, view дергает logic и просто оборачивает результат в Response.

Пример — регистрация (`tickets/logic.py`):

```python
class CreateTicketUsecase:
    def __init__(self, client: EventsProviderClient, events: EventRepository, tickets: TicketRepository):
        self.client = client
        self.events = events
        self.tickets = tickets

    def execute(self, event_id, first_name, last_name, email, seat) -> Ticket:
        event = self.events.get(event_id)
        if event is None:
            raise EventNotFound
        if event.status != EventStatus.PUBLISHED:
            raise EventUnexpectedStatus
        if timezone.now() > event.registration_deadline:
            raise RegistrationDeadlinePassed

        ticket_id = self.client.register(event.id, first_name, last_name, email, seat)
        return self.tickets.create(event=event, ticket_id=ticket_id, first_name=first_name,
                                    last_name=last_name, email=email, seat=seat)
```

В Django-варианте репозитории можно не выделять как отдельный протокол (в отличие
от FastAPI-примера в рекомендациях, где это обязательно) — используем Django ORM
напрямую внутри logic.py, но саму логику держим отдельно от view/serializer,
чтобы:
- её было легко тестировать без поднятия HTTP-слоя
- бизнес-правила (deadline, статус) не размазывались по view

## 6. Фоновая синхронизация (sync app)

- Celery periodic task `synchronize_events`, расписание — раз в сутки (celery beat)
- Broker — Postgres. Реализуется через kombu SQLAlchemy-transport
  (`broker_url = "sqla+postgresql://..."`, пакет `kombu[sqlalchemy]`), не через
  Redis/RabbitMQ — так как это явное требование
- Логика синхронизации (`sync/logic.py`):
  1. читаем `SyncMetadata.last_changed_at` (если нет записи — используем `2000-01-01`,
     это и есть "первая синхронизация")
  2. помечаем `sync_status = running`
  3. идём по `EventsPaginator(client, changed_at=last_changed_at)`, для каждого
     события — `update_or_create` в БД (Place и Event)
  4. попутно считаем максимальный `changed_at` среди полученных событий
  5. по завершении — сохраняем новый `last_changed_at`, `sync_status = idle`,
     `last_sync_time = now()`
  6. при ошибке — `sync_status = failed`, `last_error`, логируем через `logging`,
     таск не должен молча проглатывать исключение
- `POST /api/sync/trigger` — просто вызывает ту же usecase-функцию синхронно
  (или ставит celery-таск через `.delay()`, если хотим не блокировать запрос —
  решим на этапе реализации, TODO решить: sync vs async trigger)

## 7. Endpoints (соответствие требованиям)

| Endpoint | Метод | Слой |
|---|---|---|
| `/api/health/` | GET | healthcheck app, без БД-обращений или с простым SELECT 1 |
| `/api/sync/trigger/` | POST | sync app -> sync/logic.py |
| `/api/events/` | GET | events app -> из локальной БД, фильтр `date_from`, DRF pagination (PageNumberPagination) |
| `/api/events/{event_id}/` | GET | events app -> из локальной БД |
| `/api/events/{event_id}/seats/` | GET | events app -> идёт в EventsProviderClient напрямую, кэш 30 сек (Django cache framework, `cache.get_or_set`) |
| `/api/tickets/` | POST | tickets app -> CreateTicketUsecase |
| `/api/tickets/{ticket_id}/` | DELETE | tickets app -> CancelTicketUsecase |

Важные нюансы, которые логика должна учитывать:
- перед вызовом `seats` — проверять `event.status == published` на своей стороне
  (иначе поймаем кривой 500 от внешнего API)
- при регистрации — валидировать, что `seat` входит в `seats_pattern` площадки,
  до похода во внешний API (быстрый fail без лишнего запроса)
- при отмене — учитывать, что `ticket_id` во внешнем API привязан к месту, а не
  к пользователю; отмена помечает наш `Ticket.cancelled_at`, повторная попытка
  отменить уже отменённый билет должна возвращать понятную ошибку, а не тихо 200

## 8. Кэш для seats (30 секунд)

Используем `django.core.cache` (локальный in-memory backend на процесс, либо
`django-redis`, если разрешено — но это не обязательно, т.к. Redis не используется
как celery broker; для простого TTL-кэша локального backend'а Django достаточно).
Ключ кэша: `seats:{event_id}`, TTL=30.

Важно явно отметить в коде/README ограничение: если процессов web-сервера
несколько (что и есть по `run.sh` — gunicorn с несколькими workers),in-memory
кэш не будет общим между процессами — это осознанный компромисс для тестового
задания, но стоит явно про это написать в README, чтобы не выглядело как
недосмотр.

## 9. Тестирование

- `pytest` + `pytest-django`
- `EventsProviderClient` — тесты мокируют HTTP-слой через `unittest.mock`
  (mock `httpx.Client` или `responses`-подобный подход), проверяем:
  - корректный URL с trailing slash
  - парсинг успешного ответа
  - превращение 500 (неопубликованное событие) в `EventNotPublished`
  - превращение 400 "already sold" в `SeatAlreadyTaken`
- `EventsPaginator` — тест мокирует `EventsProviderClient.get_events`, проверяет:
  - что итератор проходит все страницы до `next_cursor is None`
  - что `cursor` из ответа передаётся в следующий вызов
  - что порядок событий сохраняется
- `logic.py` usecases — тесты с моками репозиториев/клиента (без реальной БД
  там, где не критично) + отдельные integration-тесты с `pytest-django` для
  проверки реальных ORM-запросов (фильтрация по `date_from`, пагинация)

## 10. CI/CD

`.github/workflows/ci.yml`:
1. `uv sync`
2. `uv run ruff check .`
3. `uv run pytest`
4. деплой — только если шаги 2-3 зелёные

## 11. Деплой / Dockerfile / run.sh

`run.sh`:
```bash
#!/bin/bash
uv run ./manage.py migrate
uv run ./manage.py collectstatic --noinput

uv run python -m celery -A src.core worker -P solo -B -l INFO &
uv run python -m gunicorn -b 0.0.0.0:8000 --workers=1 --threads=8 \
  --worker-class=gthread --timeout 120 --preload src.core.wsgi:application &
wait
```

Секреты (API_KEY внешнего сервиса, DB_URL, SECRET_KEY) — только через переменные
окружения платформы, `.env` не коммитим (в `.gitignore` сразу).

## 12. Порядок итеративной разработки (каждый пункт — отдельный деплой)

1. Базовая структура проекта, `pyproject.toml` (uv+ruff), CI с линтером,
   `/api/health/`, деплой на платформу, подключение к Postgres — убедиться,
   что всё разворачивается
2. `EventsProviderClient` + тесты (без интеграции в остальной проект пока)
3. `EventsPaginator` + тесты
4. Модели `events` (Event, Place) + миграции
5. `sync` app: `SyncMetadata`, usecase синхронизации, celery task, broker на
   Postgres, `/api/sync/trigger/`
6. `/api/events/` (список) + `/api/events/{id}/` (детали) — из локальной БД
7. `/api/events/{id}/seats/` — прямой поход во внешний API + кэш 30 сек
8. `tickets` app: модель, `/api/tickets/` (POST), `/api/tickets/{id}/` (DELETE)
9. Финальная полировка: README, покрытие тестами оставшихся мест, проверка
   что все секреты вынесены, ruff/isort чистые

Каждый пункт — отдельный PR и отдельный деплой, а не один большой коммит в конце.

## 13. Открытые вопросы (решить перед/во время реализации)

- `POST /api/sync/trigger/` — синхронно ждать завершения синхронизации в
  http-ответе, или ставить celery-таск и сразу отвечать 200 (fire-and-forget)?
- Нужна ли отдельная таблица логов синхронизации (история запусков), или
  достаточно одной строки `SyncMetadata` с последним статусом?
- Что возвращать в `/api/events/` пока синхронизация ни разу не прошла —
  пустой список или 202/503 с пояснением?
