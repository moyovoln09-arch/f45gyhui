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
hysteria2://password@host:443?up=200&down=200#name
```

Пустые строки и `# комментарии` игнорируются.

## Запуск
Базовый:

```bash
python3 proxy_tester.py --keys keys.txt
```

С параметрами:

```bash
python3 proxy_tester.py \
  --keys keys.txt \
  --top 5 \
  --timeout 30 \
  --shuffle \
  --export-config config.json \
  --show-inbound
```

### Новые функции
- `--shuffle`: Случайный порядок тестирования нод.
- `--shuffle-output`: Случайный порядок вывода в консоль (чтобы не выбирали только первый ключ).
- `--export-config`: Создает `config.json` для `sing-box` с балансировкой (`random` и `urltest`) между лучшими нодами.
- `--show-inbound`: Показывает пример конфига (и скрипт установки) для сервера Hysteria2.

## Результат
- В консоли: рейтинг топ-N.
- В файле `report.json`: подробный отчет по каждому ключу.
