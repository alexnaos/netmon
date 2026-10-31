# netmon

Сервис мониторинга локальной сети: живой скан подсети + карта сети + топология + карточки устройств с данными из внешнего сканера.

Работает как Flask-приложение; развернут на домашнем сервере (192.168.1.103:5000).

## Возможности

- **Реальное сканирование** подсети 192.168.1.0/24 при каждом открытии страницы:
  1. параллельный ping sweep (128 воркеров, таймаут 2 с);
  2. ARP-запросы для получения MAC;
  3. TCP-скан 10 типовых портов (22, 80, 443, 1883, 8123, 8080, 5000, 554, 1900, 5353).
- **Только живые устройства** — офлайн-устройства из карты не отображаются.
- **Обогащение данных** — hostname и производитель берутся из отчёта внешнего сканера (`SCANNER_DATA` в `data/network_data.py`), роутер/устройства — из базы `DEVICES`.
- **Карта сети** — интерактивные плитки с категориями, статусами и modal-карточкой (IP, hostname, vendor, MAC, RTT, порты, ссылки на сервисы).
- **Топология** — дерево соединений роутер → mesh → устройства.
- **Multi-IP хосты** — устройства с несколькими IP (один MAC, например Orange Pi `.23`/`.153` или NAS `.91`/`.186`) объединяются в одну карточку: на плитке — бейджи интерфейсов с live-статусом, активный интерфейс помечен `▶`/`★`; группы задаются в `MULTI_IP_GROUPS` (`data/network_data.py`); счётчики в шапке показывают «живых адресов — карточек».

## Структура

```
├── app/
│   ├── app.py                  # Flask-приложение (API + веб)
│   └── templates/
│       └── network_map.html    # Карта сети (фронтенд)
├── data/
│   ├── network_data.py         # База устройств + SCANNER_DATA (hostname/vendor)
│   └── network_discovery.py    # CLI-сканер для обновления network_data.py
├── requirements.txt
└── README.md
```

## API

| Endpoint | Описание |
|----------|----------|
| `GET /network` | Веб-страница карты сети |
| `GET /api/network/scan` | Реальное сканирование (ping + ARP + TCP) |
| `GET /api/network/topology` | Граф соединений |
| `GET /api/network/info` | Текущее состояние из БД |
| `GET /api/device/<ip>` | Карточка устройства |
| `GET /api/device/<ip>/services` | Сервисы устройства |

### Ответ `/api/network/scan`

```json
{
  "devices": [
    {"ip": "192.168.1.1", "name": "Keenetic AX3000", "mac": "...", "status": "online",
     "ping_rtt": 1.2, "ports": [80, 443], "hostname": "...", "vendor": "..."}
  ],
  "total_hosts": 254,
  "alive_count": 10,
  "elapsed_sec": 3.1
}
```

## Запуск

```bash
git clone https://github.com/alexnaos/netmon.git
cd netmon
python -m venv .venv
.venv/bin/pip install -r requirements.txt
nohup .venv/bin/python app/app.py > radmonitor.log 2>&1 &
```

Карта сети: http://<host>:5000/network

## Обновление базы устройств (CLI)

```bash
python data/network_discovery.py
```

Скрипт пингует подсеть, добавляет новые устройства, удаляет недоступные, обновляет порты и RTT.

## Данные сканера

`SCANNER_DATA` (в `data/network_data.py`) — словарь `{ip: {"hostname": ..., "vendor": ...}}`, импортированный из HTML-отчёта сетевого сканера. Обновляется вручную при появлении нового отчёта.

## Лицензия

MIT
