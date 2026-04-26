"""Набор алгоритмических задач в стиле competitive/predictive coding.

Запуск:
    python solver.py

Можно выбрать задачу из меню или передать аргумент через CLI:
    python solver.py two_sum "2 7 11 15" 9
    python solver.py brackets "{[()]}"
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Dict, Iterable, List, Optional, Tuple
import argparse


@dataclass(frozen=True)
class Edge:
    to: str
    weight: int


class Algorithms:
    """Коллекция решений популярных задач."""

    @staticmethod
    def two_sum(nums: List[int], target: int) -> Optional[Tuple[int, int]]:
        """Возвращает индексы двух чисел, сумма которых равна target."""
        seen: Dict[int, int] = {}
        for i, value in enumerate(nums):
            need = target - value
            if need in seen:
                return seen[need], i
            seen[value] = i
        return None

    @staticmethod
    def is_valid_brackets(s: str) -> bool:
        """Проверяет корректность скобочной последовательности."""
        pairs = {")": "(", "]": "[", "}": "{"}
        stack: List[str] = []

        for ch in s:
            if ch in "([{":
                stack.append(ch)
            elif ch in pairs:
                if not stack or stack[-1] != pairs[ch]:
                    return False
                stack.pop()

        return not stack

    @staticmethod
    def fibonacci(n: int) -> int:
        """Возвращает n-е число Фибоначчи (0-indexed), O(n)."""
        if n < 0:
            raise ValueError("n должен быть неотрицательным")
        if n <= 1:
            return n

        prev, curr = 0, 1
        for _ in range(2, n + 1):
            prev, curr = curr, prev + curr
        return curr

    @staticmethod
    def dijkstra(graph: Dict[str, List[Edge]], start: str) -> Dict[str, int]:
        """Кратчайшие расстояния от start до всех вершин неотрицательного графа."""
        dist: Dict[str, int] = {node: float("inf") for node in graph}
        dist[start] = 0
        pq: List[Tuple[int, str]] = [(0, start)]

        while pq:
            cur_dist, node = heappop(pq)
            if cur_dist > dist[node]:
                continue

            for edge in graph[node]:
                cand = cur_dist + edge.weight
                if cand < dist[edge.to]:
                    dist[edge.to] = cand
                    heappush(pq, (cand, edge.to))

        return dist



def parse_int_list(raw: str) -> List[int]:
    return [int(x) for x in raw.split() if x.strip()]


def run_cli(argv: Optional[Iterable[str]] = None) -> str:
    parser = argparse.ArgumentParser(description="Решение набора алгоритмических задач")
    sub = parser.add_subparsers(dest="cmd")

    p_two = sub.add_parser("two_sum")
    p_two.add_argument("nums", help="Список чисел через пробел")
    p_two.add_argument("target", type=int)

    p_br = sub.add_parser("brackets")
    p_br.add_argument("s")

    p_fib = sub.add_parser("fib")
    p_fib.add_argument("n", type=int)

    p_dij = sub.add_parser("demo_dijkstra")

    args = parser.parse_args(argv)

    if args.cmd == "two_sum":
        res = Algorithms.two_sum(parse_int_list(args.nums), args.target)
        return f"two_sum => {res}"

    if args.cmd == "brackets":
        return f"brackets => {Algorithms.is_valid_brackets(args.s)}"

    if args.cmd == "fib":
        return f"fib => {Algorithms.fibonacci(args.n)}"

    if args.cmd == "demo_dijkstra":
        graph = {
            "A": [Edge("B", 4), Edge("C", 2)],
            "B": [Edge("C", 1), Edge("D", 5)],
            "C": [Edge("B", 3), Edge("D", 8), Edge("E", 10)],
            "D": [Edge("E", 2)],
            "E": [],
        }
        return f"dijkstra => {Algorithms.dijkstra(graph, 'A')}"

    return (
        "Выберите задачу: two_sum, brackets, fib, demo_dijkstra\n"
        "Пример: python solver.py two_sum \"2 7 11 15\" 9"
    )


if __name__ == "__main__":
    print(run_cli())
