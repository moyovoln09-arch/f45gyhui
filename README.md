# VLESS/Trojan/Hysteria Key Tester (Linux, sing-box, Python)

Скрипт тестирует список `vless://`, `trojan://`, `hysteria://` и `hysteria2://` (hy2) ключей через локальный `sing-box`, считает средний балл и показывает **топ-5**.

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
hysteria://auth_str@host:port?up=200&down=200&obfs=magic#name
hy2://password@host:port?sni=example.com&up=200&down=200#name
```

Пустые строки и `# комментарии` игнорируются.

## Запуск
Базовый:

```bash
python3 proxy_tester.py --keys keys.txt
```

Экспорт конфигурации для sing-box (с рандомизацией):

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
  --shuffle \
  --hy-bandwidth 200
```

Для вывода примера настройки сервера Hysteria2:

```bash
python3 proxy_tester.py --print-hy2-example
```

### Рандомизация и балансировка
Для равномерного распределения нагрузки и исключения предвзятости при выборе (многие выбирают первый ключ):
- Флаг `--shuffle` перемешивает ключи перед тестированием.
- При экспорте в sing-box (`--export-singbox`) порядок нод в списке случаен.
- В сгенерированном конфиге по умолчанию выбран outbound `random` (loadbalance со стратегией random), который распределяет трафик между всеми рабочими нодами.

## Результат
- В консоли: рейтинг топ-N.
- В файле `report.json`: подробный отчет по каждому ключу.
