#!/usr/bin/env python3
# 用假 curses 验证 tui 渲染/回顾逻辑不崩溃（不测真实鼠标）
import types, json

class FakeCurses:
    A_BOLD = 1
    A_NORMAL = 0
    A_DIM = 4
    KEY_MOUSE = 409
    KEY_ENTER = 10
    KEY_DOWN = 2
    KEY_UP = 3
    KEY_RIGHT = 4
    KEY_NPAGE = 338
    KEY_PPAGE = 339
    ALL_MOUSE_EVENTS = 1
    REPORT_MOUSE_POSITION = 2
    BUTTON1_CLICKED = 4
    class error(Exception):
        pass
    class _CP:
        def __init__(self, n): self.n = n
    def color_pair(self, n): return n
    def init_pair(self, *a): pass
    def use_default_colors(self): pass
    def start_color(self): pass
    def mousemask(self, *a): pass
    def wrapper(self, fn): return fn(self.stdscr)
    stdscr = None

class FakeStd:
    def __init__(self): self.h = 30; self.w = 90; self.calls = []
    def getmaxyx(self): return (self.h, self.w)
    def clear(self): pass
    def erase(self): pass
    def refresh(self): pass
    def bkgdset(self, *a): pass
    def addstr(self, y, x, s, attr=0):
        self.calls.append((y, x, s))
    def addch(self, y, x, ch, attr=0):
        self.calls.append((y, x, ch))
    def getch(self):
        # 翻页浏览时直接退出
        return ord("q")

import tui
fc = FakeCurses()
st = FakeStd()
fc.stdscr = st
tui.curses = fc

q = {
    "id": "t1", "cat": "测试分类", "paper": "2023上",
    "q": "关于项目管理计划的描述，不正确的是（）。这是一道用于冒烟测试的题目内容，足够长以触发换行折行逻辑验证 CJK 宽度计算是否正确。",
    "opts": ["A. 选项一的内容", "B. 选项二的内容比较长用来测试折行是否正常工作并且 CJK 宽度正确",
             "C. 选项三", "D. 选项四的内容"],
    "ans": 1, "exp": "解析内容：项目管理计划应当包括所有子计划，但题目描述不正确，因此选 B。",
}
qs = [q]

# 1) 作答态渲染
r1 = tui.draw_question(st, q, 0, 1, "random", "asking", -1)
print("draw asking OK, opt_ranges:", r1)
# 2) 反馈态渲染（选错）
r2 = tui.draw_question(st, q, 0, 1, "random", "feedback", 0)
print("draw feedback(错) OK")
# 3) 反馈态（选对）
r3 = tui.draw_question(st, q, 0, 1, "random", "feedback", 1)
print("draw feedback(对) OK")
# 4) 记录态（模拟考）
r4 = tui.draw_question(st, q, 0, 1, "exam", "recorded", -1)
print("draw recorded OK")

# 5) 错题本浏览
wrong = [{"id": "t1", "cat": "测试", "q": q["q"], "opts": q["opts"], "ans": 1, "exp": q["exp"]}]
tui.paged_view(st, "错题本 (1)", [("测试行", 0)])
print("paged_view OK")

# 6) 模拟考回顾
tui.mock_review(st, [(q, 1), (q, 0)])  # 一题对一题错
print("mock_review OK")

print("ALL TUI LOGIC SMOKE PASSED")
