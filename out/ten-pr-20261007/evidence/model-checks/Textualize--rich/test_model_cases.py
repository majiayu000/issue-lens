from rich.cells import cell_len
from rich.console import Console
from rich.text import Text


def test_A_TC001_direct_console_print():
    console = Console(width=8)
    value = "123ありがとうございました"
    with console.capture() as capture:
        console.print(Text(value))
    output = capture.get()
    assert output == "123あり\nがとうご\nざいまし\nた\n"
    assert output.replace("\n", "") == value
    assert all(cell_len(line) <= 8 for line in output.splitlines())


def test_A_TC002_whole_ascii_word_moves_to_new_line():
    lines = Text("abc defg").wrap(Console(), 6)
    assert [line.plain.rstrip() for line in lines] == ["abc", "defg"]


def test_B_TC001_whole_cjk_word_moves_to_new_line():
    lines = Text("abc 中文").wrap(Console(), 6)
    assert [line.plain.rstrip() for line in lines] == ["abc", "中文"]
    assert all(cell_len(line.plain) <= 6 for line in lines)


def test_B_TC002_cjk_long_word_after_prefix():
    lines = Text("AB 中文测试").wrap(Console(), 5)
    assert [line.plain.rstrip() for line in lines] == ["AB", "中文", "测试"]
    assert all(cell_len(line.plain) <= 5 for line in lines)

