from solver import Algorithms, Edge, run_cli


def test_two_sum():
    assert Algorithms.two_sum([2, 7, 11, 15], 9) == (0, 1)
    assert Algorithms.two_sum([1, 2, 3], 7) is None


def test_brackets():
    assert Algorithms.is_valid_brackets("{[()]}") is True
    assert Algorithms.is_valid_brackets("{[(])}") is False


def test_fibonacci():
    assert Algorithms.fibonacci(0) == 0
    assert Algorithms.fibonacci(1) == 1
    assert Algorithms.fibonacci(10) == 55


def test_dijkstra():
    graph = {
        "A": [Edge("B", 1), Edge("C", 4)],
        "B": [Edge("C", 2), Edge("D", 6)],
        "C": [Edge("D", 3)],
        "D": [],
    }
    assert Algorithms.dijkstra(graph, "A") == {"A": 0, "B": 1, "C": 3, "D": 6}


def test_cli_two_sum():
    assert run_cli(["two_sum", "2 7 11 15", "9"]) == "two_sum => (0, 1)"
