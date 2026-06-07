# VLESS/Trojan/Hysteria2 Key Tester (Linux, sing-box, Python)

Скрипт тестирует список `vless://`, `trojan://` и `hysteria2://` (`hy2://`) ключей через локальный `sing-box`, считает средний балл и показывает **топ-5**.

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
hysteria2://password@host:443?sni=example.com&obfs=plain&obfs-password=pwd#name
```

Пустые строки и `# комментарии` игнорируются. Для Hysteria2 по умолчанию устанавливается скорость 200 Mbps (up/down) для лучшей производительности в играх.

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
  --report report.json \
  --export-singbox config.json
```

## Особенности
- **Поддержка Hysteria2**: Автоматическая настройка параметров для игрового использования (200 Mbps по умолчанию).
- **Экспорт в sing-box**: Флаг `--export-singbox` генерирует готовый клиентский конфиг.
- **Рандомизация**: При экспорте порядок нод перемешивается, а в качестве основного исходящего прокси (`select`) по умолчанию выбран балансировщик (`random`), который равномерно распределяет трафик между всеми рабочими серверами. Это помогает избежать нагрузки только на первый сервер в списке.
- **Перемешивание входных ключей**: Флаг `--shuffle` позволяет тестировать ключи в случайном порядке.

## Результат
- В консоли: рейтинг топ-N.
- В файле `report.json`: подробный отчет по каждому ключу.
- В файле экспорта (если указан): готовый конфиг для `sing-box`.
