# Predict Coding: набор решений задач

В репозитории реализован полноценный учебный мини-проект с несколькими классическими задачами:

- `two_sum` — поиск двух индексов с нужной суммой за `O(n)`;
- `is_valid_brackets` — валидация скобочной последовательности через стек;
- `fibonacci` — итеративный расчёт n-го числа Фибоначчи;
- `dijkstra` — кратчайшие пути в взвешенном графе.

## Быстрый старт

```bash
python solver.py
python solver.py two_sum "2 7 11 15" 9
python solver.py brackets "{[()]}"
python solver.py fib 20
python solver.py demo_dijkstra
```

## Проверка

```bash
python -m pytest -q
```
