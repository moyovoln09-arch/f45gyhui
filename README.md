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
hysteria2://pass@host:443?sni=example.com&obfs=magic&obfs-password=secret
```

Пустые строки и `# комментарии` игнорируются.

## Запуск
Базовый:

```bash
python3 proxy_tester.py --keys keys.txt
```

С экспортом в sing-box:

```bash
python3 proxy_tester.py --keys keys.txt --export-singbox config.json
```

С параметрами:

```bash
python3 proxy_tester.py \
  --keys keys.txt \
  --top 5 \
  --timeout 30 \
  --report report.json \
  --export-singbox config.json \
  --shuffle
```

## Результат
- В консоли: рейтинг топ-N.
- В файле `report.json`: подробный отчет по каждому ключу.
- В `config.json` (если указан `--export-singbox`): готовый конфиг для клиента. В конфиге ноды перемешаны, а по умолчанию стоит `random` (балансировщик) для равномерного распределения трафика.
