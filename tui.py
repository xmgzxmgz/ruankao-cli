#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tui.py : 终端鼠标 TUI 刷题界面（低调模式，伪装成测试运行器）
- 鼠标点击选项作答（也支持键盘 a/b/c/d / 1-4）
- 练习模式答完即时高亮正确/错误项并展示解析
- 模拟考试模式：作答保密，交卷后统一回顾
- 依赖 windows-curses（仅 Windows 需要；其它平台用标准 curses）
"""
import unicodedata
import curses
import time
import json
import os

# 本地化，避免以脚本方式运行时 from drill import 触发二次导入
HERE = os.path.dirname(os.path.abspath(__file__))
WFILE = os.path.join(HERE, "wrong.json")


def load_wrong():
    try:
        with open(WFILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_wrong(items):
    try:
        with open(WFILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fmt_time(sec):
    mm = int(sec // 60)
    ss = int(sec % 60)
    return "%02d:%02d" % (mm, ss)


# 颜色对
C_HEADER = 1
C_NORM = 2
C_OK = 3
C_BAD = 4
C_DIM = 5
C_TITLE = 6
C_PICK = 7


def cjk_width(s):
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def wrap(text, width):
    out = []
    cur = ""
    curw = 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if curw + cw > width and cur:
            out.append(cur)
            cur = ""
            curw = 0
        cur += ch
        curw += cw
    out.append(cur)
    return out or [""]


def s_add(win, y, x, s, attr=0, maxw=None):
    try:
        if maxw is not None and len(s) > maxw:
            s = s[:maxw]
        win.addstr(y, x, s, attr)
    except curses.error:
        pass


def paged_view(stdscr, title, lines, hint="空格/↓ 翻页 · ↑ 上翻 · q 返回"):
    """lines: list of (text, attr). 简单分页浏览。"""
    maxy, maxx = stdscr.getmaxyx()
    width = max(20, maxx - 4)
    # 预分页
    pages = []
    buf = []
    bufh = 0
    for text, attr in lines:
        for seg in wrap(text, width):
            if bufh >= maxy - 4:
                pages.append(buf)
                buf = []
                bufh = 0
            buf.append((seg, attr))
            bufh += 1
    if buf:
        pages.append(buf)
    if not pages:
        pages = [[("", 0)]]
    pi = 0
    while True:
        stdscr.clear()
        s_add(stdscr, 0, 0, " " + title, curses.color_pair(C_TITLE) | curses.A_BOLD, maxw=maxx - 1)
        s_add(stdscr, maxy - 1, 0, " " + hint + "   [%d/%d]" % (pi + 1, len(pages)),
              curses.color_pair(C_DIM), maxx - 1)
        y = 2
        for seg, attr in pages[pi]:
            s_add(stdscr, y, 2, seg, attr, maxx - 3)
            y += 1
            if y >= maxy - 2:
                break
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (ord("q"), ord("Q"), 27):  # esc
            break
        elif ch in (curses.KEY_NPAGE, ord(" "), curses.KEY_DOWN):
            pi = min(pi + 1, len(pages) - 1)
        elif ch in (curses.KEY_PPAGE, curses.KEY_UP):
            pi = max(pi - 1, 0)


def draw_question(stdscr, q, idx, total, mode, state, picked):
    """渲染当前题，返回选项行区间 opt_ranges（用于鼠标命中）。"""
    maxy, maxx = stdscr.getmaxyx()
    width = max(20, maxx - 4)
    stdscr.clear()
    # 顶部伪装条
    s_add(stdscr, 0, 0, " ruankao-test-runner   [suite loaded]",
          curses.color_pair(C_HEADER) | curses.A_BOLD, maxx - 1)
    tag = q.get("cat", "")
    if q.get("paper"):
        tag += " (" + q["paper"] + ")"
    status = " case #%s  %s   %d/%d   mode=%s" % (q["id"], tag, idx + 1, total, mode)
    s_add(stdscr, 1, 0, status, curses.color_pair(C_DIM), maxx - 1)

    y = 3
    for seg in wrap(q["q"], width):
        s_add(stdscr, y, 2, seg, curses.color_pair(C_TITLE), maxx - 3)
        y += 1
    y += 1

    opt_ranges = []
    for i, o in enumerate(q["opts"]):
        start = y
        attr = curses.color_pair(C_NORM)
        prefix = "  %s " % o[:2]  # "A. "
        body = o[2:] if len(o) > 2 else ""
        # 反馈态高亮
        if state in ("feedback", "recorded"):
            if i == q["ans"]:
                attr = curses.color_pair(C_OK) | curses.A_BOLD
            elif i == picked:
                attr = curses.color_pair(C_BAD) | curses.A_BOLD
        first = True
        for seg in wrap(body, width - len(prefix)):
            line = (prefix if first else " " * len(prefix)) + seg
            s_add(stdscr, y, 2, line, attr, maxx - 3)
            first = False
            y += 1
        opt_ranges.append((start, y - 1))
        y += 1

    # 反馈/记录态：解析
    if state == "feedback":
        y += 1
        verdict = " => assertion PASS  OK" if picked == q["ans"] else " => assertion FAIL  expected: " + q["opts"][q["ans"]][:2]
        vattr = curses.color_pair(C_OK) if picked == q["ans"] else curses.color_pair(C_BAD)
        s_add(stdscr, y, 2, verdict, vattr | curses.A_BOLD, maxx - 3)
        y += 1
        if q.get("exp"):
            for seg in wrap("note: " + q["exp"], width - 2):
                s_add(stdscr, y, 4, seg, curses.color_pair(C_DIM), maxx - 5)
                y += 1
        s_add(stdscr, maxy - 1, 0, " 回车/点击 下一题 · [w] 错题本 · [q] 退出",
              curses.color_pair(C_DIM), maxx - 1)
    elif state == "recorded":
        s_add(stdscr, y, 2, " 已记录（答案交卷后揭晓）", curses.color_pair(C_DIM), maxx - 3)
        s_add(stdscr, maxy - 1, 0, " 回车/点击 下一题 · [q] 交卷",
              curses.color_pair(C_DIM), maxx - 1)
    else:
        s_add(stdscr, maxy - 1, 0, " a/b/c/d 或 鼠标点击选项作答 · [n] 跳过 · [w] 错题 · [q] 退出",
              curses.color_pair(C_DIM), maxx - 1)
    stdscr.refresh()
    return opt_ranges


def mock_review(stdscr, records):
    n = len(records)
    passed = 0
    for q, pk in records:
        if pk == q["ans"]:
            passed += 1
    acc = passed / n * 100 if n else 0
    pass_line = 45 if n >= 75 else (n * 3 + 4) // 5

    lines = []
    lines.append(("==== 模拟考试结果 ====", curses.color_pair(C_TITLE) | curses.A_BOLD))
    lines.append(("得分: %d / %d   %s" % (passed, n, "通过 ✅" if passed >= pass_line else "未通过 ❌"),
                  curses.color_pair(C_OK) if passed >= pass_line else curses.color_pair(C_BAD)))
    lines.append(("正确率: %.1f%%   及格线: %d" % (acc, pass_line), curses.color_pair(C_NORM)))
    lines.append(("", 0))
    # 分类明细
    cat_stat = {}
    for q, pk in records:
        c = q["cat"]
        st = cat_stat.setdefault(c, [0, 0])
        st[1] += 1
        if pk == q["ans"]:
            st[0] += 1
    lines.append(("-- 分类明细 --", curses.color_pair(C_DIM)))
    for c in sorted(cat_stat, key=lambda x: -cat_stat[x][0] / cat_stat[x][1]):
        ok, tot = cat_stat[c]
        lines.append(("  %-22s %d/%d (%.0f%%)" % (c, ok, tot, ok / tot * 100),
                      curses.color_pair(C_NORM)))
    lines.append(("", 0))
    lines.append(("-- 错题回顾 --", curses.color_pair(C_TITLE) | curses.A_BOLD))
    for q, pk in records:
        if pk == q["ans"]:
            continue
        lines.append(("#%s [%s]" % (q["id"], q["cat"]), curses.color_pair(C_DIM)))
        for seg in wrap(q["q"], 70):
            lines.append(("  " + seg, curses.color_pair(C_NORM)))
        for i, o in enumerate(q["opts"]):
            mark = ""
            if i == q["ans"]:
                mark = "✓ "
                a = curses.color_pair(C_OK)
            elif i == pk:
                mark = "✗ "
                a = curses.color_pair(C_BAD)
            else:
                mark = "  "
                a = curses.color_pair(C_NORM)
            for k, seg in enumerate(wrap(o, 66)):
                lines.append(("    " + (mark if k == 0 else "  ") + seg, a))
        if q.get("exp"):
            for seg in wrap("note: " + q["exp"], 66):
                lines.append(("    " + seg, curses.color_pair(C_DIM)))
        lines.append(("", 0))
    paged_view(stdscr, "模拟考试回顾", lines)


def run_tui(qs, mode, instant=True, num=75, minutes=150):
    """TUI 主入口。instant=True 表示答完即时反馈（练习模式）；False 为模拟考（保密）。"""
    import random
    random.shuffle(qs)
    if num and num < len(qs):
        qs = qs[:num]
    total = len(qs)
    wrong = load_wrong()
    wrong_ids = {w["id"] for w in wrong}
    records = []  # (q, picked) 模拟考用
    start = time.time()
    limit = minutes * 60

    idx = 0
    state = "asking"
    picked = -1

    def main_loop(stdscr):
        nonlocal idx, state, picked
        curses.curs_set(0)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.start_color()
        # 用纯黑底色，避免 Windows Terminal 默认灰底导致"雾蒙蒙"
        curses.init_pair(C_HEADER, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(C_NORM, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(C_OK, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(C_BAD, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(C_DIM, 242, curses.COLOR_BLACK)  # 暗灰色（比 COLOR_YELLOW 柔和）
        curses.init_pair(C_TITLE, curses.COLOR_WHITE | curses.A_BOLD, curses.COLOR_BLACK)
        curses.init_pair(C_PICK, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # 全局底色：确保每格都有黑底白字，彻底消除残影
        stdscr.bkgd(' ', curses.color_pair(C_NORM))
        stdscr.refresh()

        opt_ranges = []
        while idx < total:
            q = qs[idx]
            if not instant:
                remain = limit - (time.time() - start)
                if remain <= 0:
                    stdscr.clear()
                    s_add(stdscr, 0, 0, " == 时间到，自动交卷 ==", curses.color_pair(C_BAD) | curses.A_BOLD)
                    stdscr.refresh()
                    time.sleep(1.2)
                    break
            opt_ranges = draw_question(stdscr, q, idx, total, mode, state, picked)
            ch = stdscr.getch()
            if ch == curses.KEY_MOUSE:
                try:
                    _, mx, my, _, bstate = curses.getmouse()
                except Exception:
                    continue
                # 反馈/记录态：任意点击继续
                if state in ("feedback", "recorded"):
                    if bstate & curses.BUTTON1_CLICKED:
                        advance()
                    continue
                # 作答态：命中某个选项
                if bstate & curses.BUTTON1_CLICKED:
                    for i, (ys, ye) in enumerate(opt_ranges):
                        if ys <= my <= ye:
                            do_answer(i)
                            break
                continue
            # 键盘
            if ch in (ord("q"), ord("Q")):
                if state in ("asking",):
                    break
                else:
                    advance()
                continue
            if ch in (ord("w"), ord("W")):
                lines = []
                if not wrong:
                    lines.append(("错题本为空", curses.color_pair(C_OK)))
                for w in wrong:
                    lines.append(("#%s [%s]" % (w["id"], w["cat"]), curses.color_pair(C_DIM)))
                    for seg in wrap(w["q"], 66):
                        lines.append(("  " + seg, curses.color_pair(C_NORM)))
                    for i, o in enumerate(w["opts"]):
                        mark = ">" if i == w["ans"] else " "
                        lines.append(("   %s %s" % (mark, o), curses.color_pair(C_NORM)))
                    if w.get("exp"):
                        for seg in wrap("note: " + w["exp"], 66):
                            lines.append(("    " + seg, curses.color_pair(C_DIM)))
                    lines.append(("", 0))
                paged_view(stdscr, "错题本 (%d)" % len(wrong), lines)
                continue
            if state in ("feedback", "recorded"):
                if ch in (curses.KEY_ENTER, ord("\n"), ord("\r"), ord(" "), curses.KEY_RIGHT):
                    advance()
                continue
            # 作答态
            if ch in (ord("n"), ord("N")):
                records.append((q, -1))
                advance()
                continue
            pick = -1
            if ch in (ord("a"), ord("A"), ord("1")):
                pick = 0
            elif ch in (ord("b"), ord("B"), ord("2")):
                pick = 1
            elif ch in (ord("c"), ord("C"), ord("3")):
                pick = 2
            elif ch in (ord("d"), ord("D"), ord("4")):
                pick = 3
            if pick != -1:
                do_answer(pick)

        # 收尾
        if not instant:
            _finalize_mock(stdscr, records, wrong, start)
        else:
            _finalize_practice(stdscr, wrong)

    def do_answer(i):
        nonlocal state, picked
        q = qs[idx]
        picked = i
        if instant:
            if picked == q["ans"]:
                if q["id"] in wrong_ids:
                    wrong[:] = [w for w in wrong if w["id"] != q["id"]]
                    wrong_ids.discard(q["id"])
            else:
                if q["id"] not in wrong_ids:
                    wrong.append({"id": q["id"], "cat": q["cat"], "q": q["q"],
                                  "opts": q["opts"], "ans": q["ans"], "exp": q["exp"],
                                  "picked": picked})
                    wrong_ids.add(q["id"])
            state = "feedback"
        else:
            records.append((q, picked))
            state = "recorded"

    def advance():
        nonlocal idx, state, picked
        idx += 1
        state = "asking"
        picked = -1

    def _finalize_practice(stdscr):
        save_wrong(wrong)
        maxy, maxx = stdscr.getmaxyx()
        stdscr.clear()
        s_add(stdscr, 1, 2, "session summary", curses.color_pair(C_TITLE) | curses.A_BOLD, maxx - 3)
        s_add(stdscr, 3, 2, "错题本: %d 题（已写入 wrong.json）" % len(wrong),
              curses.color_pair(C_NORM), maxx - 3)
        s_add(stdscr, maxy - 1, 0, " 任意键退出", curses.color_pair(C_DIM), maxx - 1)
        stdscr.refresh()
        stdscr.getch()

    def _finalize_mock(stdscr, recs, wlist, t0):
        # 错题入错题本
        for q, pk in recs:
            if pk != q["ans"] and q["id"] not in {w["id"] for w in wlist}:
                wlist.append({"id": q["id"], "cat": q["cat"], "q": q["q"],
                              "opts": q["opts"], "ans": q["ans"], "exp": q["exp"], "picked": pk})
        save_wrong(wlist)
        mock_review(stdscr, recs)

    try:
        curses.wrapper(main_loop)
    except Exception as e:
        # 兜底：任何 TUI 异常退回 CLI 行为
        raise
