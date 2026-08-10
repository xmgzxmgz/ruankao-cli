#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruankao : 终端软考高项刷题器（低调模式）
外观像在跑单元测试 / 看构建日志，实际上在刷软考高项题。
零依赖：仅需 Python3 标准库，不联网、无弹窗、纯键盘。
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QFILE = os.path.join(HERE, "questions.json")
WFILE = os.path.join(HERE, "wrong.json")
VERSION = "1.0.0"

R = "\033[0m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREY = "\033[90m"


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
    print(DIM + "命令行（启动前）: ruankao [--cat 分类] [--wrong] [--list-cats] [-h]" + R)
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
    print(GREY + "case #" + str(q["id"]) + "  [" + q["cat"] + "]" + R)
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


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ruankao",
        description="ruankao-test-runner : 终端软考高项刷题器（低调模式）")
    ap.add_argument("-v", "--version", action="version",
                    version="ruankao " + VERSION)
    ap.add_argument("--cat", metavar="分类",
                    help="只练习指定分类，如 '计算' / '采购管理'")
    ap.add_argument("--wrong", action="store_true",
                    help="只复习错题本中的题（答对自动移出）")
    ap.add_argument("--list-cats", action="store_true",
                    help="列出所有分类后退出")
    args = ap.parse_args(argv)

    data = load_questions()
    qs = list(data.get("questions", []))
    if not qs:
        print(RED + "题库为空" + R)
        sys.exit(1)

    cats = sorted(set(q["cat"] for q in qs))
    if args.list_cats:
        print(DIM + "可用分类:" + R)
        for c in cats:
            print("  " + c)
        return

    mode = "random"
    if args.wrong:
        wrong = load_wrong()
        ids = {w["id"] for w in wrong}
        qs = [q for q in qs if q["id"] in ids]
        mode = "wrong-box(" + str(len(qs)) + ")"
        if not qs:
            print(GREEN + "错题本为空，无需复习" + R)
            sys.exit(0)
    elif args.cat:
        qs = [q for q in qs if q["cat"] == args.cat]
        mode = "cat=" + args.cat
        if not qs:
            print(RED + "未找到分类: " + args.cat + R)
            print(DIM + "可用分类: " + ", ".join(cats) + R)
            sys.exit(1)

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


if __name__ == "__main__":
    main()
