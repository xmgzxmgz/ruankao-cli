#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruankao : 终端软考高项刷题器（低调模式）
外观像在跑单元测试 / 看构建日志，实际上在刷软考高项题。
零依赖：仅需 Python3 标准库，不联网、无弹窗、纯键盘。

模式：
  ruankao                随机练全部
  ruankao --cat 计算     按分类练
  ruankao --wrong        只复习错题本
  ruankao --paper 2023上  练某年试卷
  ruankao --papers       列出所有往年试卷
  ruankao --mock         模拟考试（75题/150分钟，结束出分+回顾）
"""
import argparse
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
QFILE = os.path.join(HERE, "questions.json")
WFILE = os.path.join(HERE, "wrong.json")
VERSION = "1.1.0"

R = "\033[0m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREY = "\033[90m"
BOLD = "\033[1m"


def load_questions():
    try:
        with open(QFILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(RED + "未找到题库 questions.json（应与本脚本同目录）" + R)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(RED + "题库解析失败: " + str(e) + R)
        sys.exit(1)


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


def banner(n, mode="random"):
    print(DIM + "+" + "-" * 58 + "+")
    print("| ruankao-test-runner   suite loaded : " + str(n) +
          " cases" + " " * max(0, 18 - len(str(n))) + "|")
    print("| mode: " + mode + "   [a-d] answer  [n] skip  [w] wrong  [q] quit |")
    print("+" + "-" * 58 + "+" + R)


def show_help():
    print(DIM + "commands:" + R)
    print("  a/b/c/d 或 1/2/3/4   作答")
    print("  n           跳过本题（不判分）")
    print("  w           查看错题本")
    print("  r           重做当前题")
    print("  h           显示本帮助")
    print("  q           退出（自动保存错题本）")
    print()
    print(DIM + "命令行（启动前）: ruankao [--cat 分类] [--wrong] [--paper 年份] [--mock] [--papers] [-h]" + R)
    print()


def normalize(s):
    s = s.strip().lower()
    if s in ("a", "1"):
        return 0
    if s in ("b", "2"):
        return 1
    if s in ("c", "3"):
        return 2
    if s in ("d", "4"):
        return 3
    return -1


def show_question(q):
    print()
    tag = " [" + q["cat"] + "]"
    if q.get("paper"):
        tag += " (" + q["paper"] + ")"
    print(GREY + "case #" + str(q["id"]) + tag + R)
    print("  " + q["q"])
    for o in q["opts"]:
        print("    " + o)
    print()


def judge(q, pick, wrong):
    correct = q["ans"]
    if pick == correct:
        print(GREEN + "  => assertion PASS  OK" + R)
        return True
    print(RED + "  => assertion FAIL  expected: " + q["opts"][correct][:2] + R)
    print(DIM + "  note: " + q["exp"] + R)
    if not any(w["id"] == q["id"] for w in wrong):
        wrong.append({"id": q["id"], "cat": q["cat"], "q": q["q"],
                      "opts": q["opts"], "ans": correct, "exp": q["exp"],
                      "picked": pick})
    return False


def show_wrong(wrong):
    if not wrong:
        print(GREEN + "  错题本为空，全部清空" + R)
        return
    print(YELLOW + "  错题本 (" + str(len(wrong)) + "):" + R)
    for w in wrong:
        print(GREY + "  #" + str(w["id"]) + " [" + w["cat"] + "]" + R)
        print("   " + w["q"])
        for o in w["opts"]:
            mark = ">" if o[:2] == ("ABCD"[w["ans"]] + ".") else " "
            print("     " + mark + " " + o)
        print(DIM + "  note: " + w["exp"] + R)
        print()


def fmt_time(sec):
    mm = int(sec // 60)
    ss = int(sec % 60)
    return "%02d:%02d" % (mm, ss)


def run_practice(qs, mode):
    random.shuffle(qs)
    wrong = load_wrong()
    passed = 0
    failed = 0
    idx = 0
    banner(len(qs), mode)
    print(DIM + "  输入 h 查看命令；开始运行测试套件..." + R)
    print()
    try:
        while idx < len(qs):
            q = qs[idx]
            show_question(q)
            while True:
                try:
                    cmd = input(CYAN + "  >> " + R).strip().lower()
                except EOFError:
                    cmd = "q"
                if cmd in ("q", "quit", "exit"):
                    idx = len(qs)
                    break
                if cmd in ("h", "?"):
                    show_help()
                    continue
                if cmd in ("n", "skip"):
                    print(DIM + "  >> skipped" + R)
                    break
                if cmd in ("w", "wrong"):
                    show_wrong(wrong)
                    continue
                if cmd in ("r", "redo"):
                    continue
                pick = normalize(cmd)
                if pick == -1:
                    print(DIM + "  ?? 无效输入，输入 a/b/c/d 或 n/w/q" + R)
                    continue
                if judge(q, pick, wrong):
                    passed += 1
                    wrong[:] = [w for w in wrong if w["id"] != q["id"]]
                else:
                    failed += 1
                break
            if idx >= len(qs):
                break
            idx += 1
    except KeyboardInterrupt:
        print()
        print(DIM + "  (interrupted)" + R)
    _summary(passed, failed, wrong)


def run_mock(qs, minutes, num):
    random.shuffle(qs)
    if num and num < len(qs):
        qs = qs[:num]
    n = len(qs)
    start = time.time()
    limit = minutes * 60
    passed = 0
    records = []  # (q, picked)
    idx = 0
    banner(n, "exam %dm" % minutes)
    print(BOLD + "  模拟考试：%d 题 / 限时 %d 分钟 / 高项 45 分及格(60%%)" % (n, minutes) + R)
    print(DIM + "  作答后仅记录对错，结束统一回顾解析。a/b/c/d 作答，n 跳过(计0分)，q 交卷。" + R)
    print()
    try:
        while idx < n:
            q = qs[idx]
            show_question(q)
            while True:
                remaining = limit - (time.time() - start)
                if remaining <= 0:
                    print(RED + "  == 时间到，自动交卷 ==" + R)
                    idx = n
                    break
                try:
                    cmd = input(CYAN + "  [%d/%d 剩余%s] >> " % (idx + 1, n, fmt_time(remaining)) + R).strip().lower()
                except EOFError:
                    cmd = "q"
                if cmd in ("q", "quit"):
                    print(DIM + "  == 交卷 ==" + R)
                    idx = n
                    break
                if cmd in ("n", "skip"):
                    records.append((q, -1))
                    print(DIM + "  >> 跳过(计0分)" + R)
                    break
                pick = normalize(cmd)
                if pick == -1:
                    print(DIM + "  ?? 无效，a/b/c/d 或 n" + R)
                    continue
                records.append((q, pick))
                if pick == q["ans"]:
                    passed += 1
                    print(GREEN + "  >> 记录 √" + R)
                else:
                    print(RED + "  >> 记录 ×" + R)
                break
            if idx >= n:
                break
            idx += 1
    except KeyboardInterrupt:
        print(DIM + "\n  (interrupted, 交卷)" + R)

    elapsed = int(time.time() - start)
    wrong_list = load_wrong()
    # 评分与回顾
    print()
    print(BOLD + "+" + "-" * 58 + "+" + R)
    print("| 模拟考试结果" + " " * 46 + "|")
    acc = (passed / n * 100) if n else 0
    pass_line = 45 if n >= 75 else (n * 3 + 4) // 5  # 高项 45/75；不足75按比例约60%
    is_pass = passed >= pass_line
    print("| 得分: " + str(passed) + " / " + str(n) +
          ("  通过 ✅" if is_pass else "  未通过 ❌") + " " * 18 + "|")
    print("| 正确率: %.1f%%   及格线: %d   用时: %s" % (acc, pass_line, fmt_time(elapsed)) + " " * 8 + "|")
    print("+" + "-" * 58 + R)

    # 分类明细
    cat_stat = {}
    for q, pk in records:
        c = q["cat"]
        st = cat_stat.setdefault(c, [0, 0])
        st[1] += 1
        if pk == q["ans"]:
            st[0] += 1
    print(DIM + "\n  分类明细:" + R)
    for c in sorted(cat_stat, key=lambda x: -cat_stat[x][0] / cat_stat[x][1]):
        ok, tot = cat_stat[c]
        print("    %-22s %d/%d  (%.0f%%)" % (c, ok, tot, ok / tot * 100))

    # 错题回顾
    wrong_records = [(q, pk) for q, pk in records if pk != q["ans"]]
    print(BOLD + "\n  错题回顾 (%d):" % len(wrong_records) + R)
    for q, pk in wrong_records:
        print(GREY + "  #" + str(q["id"]) + " [" + q["cat"] + "]" + R)
        print("   " + q["q"])
        for i, o in enumerate(q["opts"]):
            mark = ""
            if i == q["ans"]:
                mark = GREEN + "✓ "
            elif i == pk:
                mark = RED + "✗ "
            else:
                mark = "  "
            print("    " + mark + o + R)
        print(DIM + "  note: " + q["exp"] + R)
        print()
        # 计入错题本
        if not any(w["id"] == q["id"] for w in wrong_list):
            wrong_list.append({"id": q["id"], "cat": q["cat"], "q": q["q"],
                               "opts": q["opts"], "ans": q["ans"], "exp": q["exp"],
                               "picked": pk})

    save_wrong(wrong_list)
    print(DIM + "  错题已写入 wrong.json，可用 ruankao --wrong 复习" + R)


def _summary(passed, failed, wrong):
    total = passed + failed
    print()
    print(DIM + "+" + "-" * 58 + "+" + R)
    print("| session summary" + " " * 44 + "|")
    print("| answered: " + str(total) + "   PASS: " + str(passed) +
          "   FAIL: " + str(failed) + "   wrong-box: " + str(len(wrong)) + " |")
    if total:
        rate = passed / total * 100
        print("| accuracy: " + ("%.1f" % rate) +
              " " * max(0, 46 - len("%.1f" % rate)) + "|")
    print("+" + "-" * 58)
    print(R, end="")
    save_wrong(wrong)
    print(DIM + "  错题本已写入 wrong.json，下次可用 --wrong 复习" + R)


def list_papers(data):
    papers = sorted(set(q.get("paper") for q in data.get("questions", []) if q.get("paper")))
    print(DIM + "可用往年试卷:" + R)
    for p in papers:
        cnt = sum(1 for q in data["questions"] if q.get("paper") == p)
        print("  %s  (%d 题)" % (p, cnt))
    print(DIM + "\n用法: ruankao --paper 2023上" + R)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ruankao",
        description="ruankao-test-runner : 终端软考高项刷题器（低调模式）")
    ap.add_argument("-v", "--version", action="version", version="ruankao " + VERSION)
    ap.add_argument("--cat", metavar="分类", help="只练习指定分类")
    ap.add_argument("--wrong", action="store_true", help="只复习错题本（答对自动移出）")
    ap.add_argument("--list-cats", action="store_true", help="列出所有分类后退出")
    ap.add_argument("--paper", metavar="年份", help="练习指定往年试卷，如 2023上")
    ap.add_argument("--papers", action="store_true", help="列出所有往年试卷后退出")
    ap.add_argument("--mock", action="store_true", help="模拟考试（75题/150分钟）")
    ap.add_argument("--num", type=int, default=75, help="模拟考试题数（默认75）")
    ap.add_argument("--time", type=int, default=150, help="模拟考试限时分钟（默认150）")
    args = ap.parse_args(argv)

    data = load_questions()
    qs_all = list(data.get("questions", []))
    if not qs_all:
        print(RED + "题库为空" + R)
        sys.exit(1)

    if args.papers:
        list_papers(data)
        return

    if args.list_cats:
        cats = sorted(set(q["cat"] for q in qs_all))
        print(DIM + "可用分类:" + R)
        for c in cats:
            print("  " + c)
        return

    cats = sorted(set(q["cat"] for q in qs_all))

    if args.paper:
        qs = [q for q in qs_all if q.get("paper") == args.paper]
        if not qs:
            print(RED + "未找到试卷: " + args.paper + R)
            print(DIM + "可用: " + ", ".join(sorted(set(q.get("paper") for q in qs_all if q.get("paper")))) + R)
            sys.exit(1)
        run_practice(qs, "paper=" + args.paper)
        return

    if args.mock:
        run_mock(qs_all, args.time, args.num)
        return

    if args.wrong:
        wrong = load_wrong()
        ids = {w["id"] for w in wrong}
        qs = [q for q in qs_all if q["id"] in ids]
        if not qs:
            print(GREEN + "错题本为空，无需复习" + R)
            sys.exit(0)
        run_practice(qs, "wrong-box(%d)" % len(qs))
        return

    if args.cat:
        qs = [q for q in qs_all if q["cat"] == args.cat]
        if not qs:
            print(RED + "未找到分类: " + args.cat + R)
            print(DIM + "可用: " + ", ".join(cats) + R)
            sys.exit(1)
        run_practice(qs, "cat=" + args.cat)
        return

    run_practice(qs_all, "random")


if __name__ == "__main__":
    main()
