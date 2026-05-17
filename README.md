# VLESS/Trojan/Hysteria2 Key Tester (Linux, sing-box, Python)

Скрипт тестирует список `vless://`, `trojan://` и `hysteria2://` ключей через локальный `sing-box`, считает средний балл и показывает **топ-5**.

## Что проверяет
- Сайты: `google`, `youtube`, `github`, `cloudflare` (успешность + задержка, ~30 сек).
- YouTube: реальная попытка скачивания через `yt-dlp` (скорость по объему скачанных данных).
- Torrent: проверка загрузки по magnet через `aria2c` (скорость по объему скачанных данных).
- Стабильность: на базе процента успешных запросов + латентности.

## Установка
Требуется Python 3.9+ и `sing-box`.

Если не хватает `aria2c`/`yt-dlp`, можно запускать с автоустановкой:

```bash
python3 proxy_tester.py --keys keys.txt --auto-install
```

Скрипт сам использует:
- `apt-get` (для `aria2` если доступно)
- `python3 -m pip install yt-dlp --break-system-packages`

## Формат файла ключей
`keys.txt` — один ключ в строке:

```text
vless://uuid@host:443?security=tls&sni=example.com&type=ws&path=%2Fws#name
trojan://password@host:443?security=tls&sni=example.com#name
hysteria2://password@host:443?sni=example.com&obfs=emerald&obfs-password=secret#name
```

Пустые строки и `# комментарии` игнорируются. Для Hysteria2 значения `up_mbps` и `down_mbps` по умолчанию равны 200.

## Запуск
Базовый:

```bash
python3 proxy_tester.py --keys keys.txt
```

С параметрами рандомизации и экспорта:

```bash
python3 proxy_tester.py \
  --keys keys.txt \
  --top 5 \
  --shuffle \
  --export-singbox config.json \
  --shuffle-output
```

- `--shuffle`: Перемешать ключи перед тестированием.
- `--export-singbox`: Путь для экспорта итогового конфига sing-box.
- `--no-shuffle-output`: Отключить случайный порядок нод в экспортируемом конфиге (по умолчанию включено).

В экспортированном конфиге по умолчанию включен `balancer` со стратегией `random`, что обеспечивает равномерное распределение нагрузки.

## Результат
- В консоли: рейтинг топ-N.
- В файле `report.json`: подробный отчет по каждому ключу.
- В указанном `--export-singbox`: готовый клиентский конфиг.
