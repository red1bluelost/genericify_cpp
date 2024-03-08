#!/usr/bin/env python

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import datasets

BASE_PROMPT_PREFIX: str = "Make the following function generic for "
CONCEPTS_PROMPT_PREFIX: str = (
    "Constrain the generic code using C++20 Concepts so that "
)
SFINAE_PROMPT_PREFIX: str = (
    "Constrain the generic code using C++17 SFINAE so that "
)

COMMANDS: list[str] = ["skip", "exit", ""]
COMMANDS_MESSAGE = (
    f'Please enter a command [{", ".join(COMMANDS)}] when ready: '
)

EMPTY_MAIN = "int main() {}"

STD_NAME_RE = re.compile(r"([^\w_]|^)(string|vector|map|abs)([^\w_])")


def write(path, content):
    with open(path, "w") as f:
        f.write(content)


def read(path) -> str:
    with open(path, "r") as f:
        return f.read()


def strip_code(code: str) -> str:
    return "\n".join(
        c
        for c in code.splitlines()
        if not c.startswith("using namespace") and not c.startswith("#include")
    )


def add_std(code: str) -> str:
    return STD_NAME_RE.sub(r"\1std::\2\3", code)


def gen_loop(out, hep, start: int, count: int):
    for idx in range(start, min(len(hep), start + count)):
        print(f"========================== {idx} ==========================")

        doc = hep[idx]
        code: str = doc["declaration"] + doc["canonical_solution"]
        test: str = doc["test"]
        if any(
            s in code or s in test for s in ["boost/any.hpp", "openssl/md5.h"]
        ):
            print(f"skipping index {idx} due to containing non-std headers")
            continue

        with tempfile.TemporaryDirectory() as td:
            base_prompt_path = os.path.join(td, "base_prompt.txt")
            sfinae_prompt_path = os.path.join(td, "sfinae_prompt.txt")
            concepts_prompt_path = os.path.join(td, "concepts_prompt.txt")

            starter_path = os.path.join(td, "starter.cpp")

            base_path = os.path.join(td, "base.cpp")
            sfinae_path = os.path.join(td, "sfinae.cpp")
            concepts_path = os.path.join(td, "concepts.cpp")

            tests_path = os.path.join(td, "tests.cpp")
            invalids_path = os.path.join(td, "invalids.cpp")

            code = strip_code(code)
            code = add_std(code)
            write(starter_path, code)
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", starter_path]
            )

            print(f"Please fix up starter code: {starter_path}")
            while (resp := input(COMMANDS_MESSAGE).strip()) not in COMMANDS:
                pass
            match resp:
                case "exit":
                    return
                case "skip":
                    continue
                case _:
                    pass

            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", starter_path]
            )
            starter_code = read(starter_path)

            write(base_path, starter_code)
            write(base_prompt_path, BASE_PROMPT_PREFIX)

            print(f"Please edit base code: {base_path}")
            print(f"Please edit base prompt: {base_prompt_path}")
            while (resp := input(COMMANDS_MESSAGE).strip()) not in COMMANDS:
                pass
            match resp:
                case "exit":
                    return
                case "skip":
                    continue
                case _:
                    pass

            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", base_path]
            )
            base_code = read(base_path)

            write(sfinae_path, base_code)
            write(concepts_path, base_code)

            write(sfinae_prompt_path, SFINAE_PROMPT_PREFIX)
            write(concepts_prompt_path, CONCEPTS_PROMPT_PREFIX)

            write(tests_path, test)
            write(invalids_path, EMPTY_MAIN)

            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", tests_path]
            )
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", invalids_path]
            )

            print(f"Please edit sfinae code: {sfinae_path}")
            print(f"Please edit sfinae prompt: {sfinae_prompt_path}")
            print(f"Please edit concepts code: {concepts_path}")
            print(f"Please edit concepts prompt: {concepts_prompt_path}")
            print(f"Please edit tests code: {tests_path}")
            print(f"Please edit invalids prompt: {invalids_path}")
            while (resp := input(COMMANDS_MESSAGE).strip()) not in COMMANDS:
                pass
            match resp:
                case "exit":
                    return
                case "skip":
                    continue
                case _:
                    pass
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", sfinae_path]
            )
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", concepts_path]
            )
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", tests_path]
            )
            subprocess.check_call(
                ["clang-format", "-i", "-style=Google", invalids_path]
            )

            gdoc = dict(
                task_id=f"HEP/{idx}",
                base_prompt=read(base_prompt_path),
                sfinae_prompt=read(sfinae_prompt_path),
                concepts_prompt=read(concepts_prompt_path),
                starter_code=read(starter_path),
                base_canonical_solution=read(base_path),
                sfinae_canonical_solution=read(sfinae_path),
                concepts_canonical_solution=read(concepts_path),
                tests=read(tests_path),
                invalids=read(invalids_path),
            )
            print(json.dumps(gdoc, sort_keys=True), file=out, flush=True)
            print()


def rework(j):
    with tempfile.TemporaryDirectory() as td:
        base_prompt_path = os.path.join(td, "base_prompt.txt")
        write(base_prompt_path, j["base_prompt"])
        sfinae_prompt_path = os.path.join(td, "sfinae_prompt.txt")
        write(sfinae_prompt_path, j["sfinae_prompt"])
        concepts_prompt_path = os.path.join(td, "concepts_prompt.txt")
        write(concepts_prompt_path, j["concepts_prompt"])

        starter_path = os.path.join(td, "starter.cpp")
        write(starter_path, j["starter_code"])

        base_path = os.path.join(td, "base.cpp")
        write(base_path, j["base_canonical_solution"])
        sfinae_path = os.path.join(td, "sfinae.cpp")
        write(sfinae_path, j["sfinae_canonical_solution"])
        concepts_path = os.path.join(td, "concepts.cpp")
        write(concepts_path, j["concepts_canonical_solution"])

        tests_path = os.path.join(td, "tests.cpp")
        write(tests_path, j["tests"])
        invalids_path = os.path.join(td, "invalids.cpp")
        write(invalids_path, j["invalids"])

        for p in [
            starter_path,
            base_path,
            sfinae_path,
            concepts_path,
            tests_path,
            invalids_path,
        ]:
            subprocess.check_call(["clang-format", "-i", "-style=Google", p])

        print(f"Please edit starter code: {starter_path}")
        print(f"Please edit base code: {base_path}")
        print(f"Please edit base prompt: {base_prompt_path}")
        print(f"Please edit sfinae code: {sfinae_path}")
        print(f"Please edit sfinae prompt: {sfinae_prompt_path}")
        print(f"Please edit concepts code: {concepts_path}")
        print(f"Please edit concepts prompt: {concepts_prompt_path}")
        print(f"Please edit tests code: {tests_path}")
        print(f"Please edit invalids prompt: {invalids_path}")
        while (resp := input(COMMANDS_MESSAGE).strip()) not in COMMANDS:
            pass
        match resp:
            case "exit":
                return j
            case "skip":
                return j
            case _:
                pass

        for p in [
            starter_path,
            base_path,
            sfinae_path,
            concepts_path,
            tests_path,
            invalids_path,
        ]:
            subprocess.check_call(["clang-format", "-i", "-style=Google", p])

        return dict(
            task_id=j["task_id"],
            base_prompt=read(base_prompt_path),
            sfinae_prompt=read(sfinae_prompt_path),
            concepts_prompt=read(concepts_prompt_path),
            starter_code=read(starter_path),
            base_canonical_solution=read(base_path),
            sfinae_canonical_solution=read(sfinae_path),
            concepts_canonical_solution=read(concepts_path),
            tests=read(tests_path),
            invalids=read(invalids_path),
        )


def fix(args):
    jsonl: str = args.jsonl
    task_id: str = args.task_id

    js = []
    with open(jsonl, "r") as f:
        for line in f:
            j = json.loads(line)
            if j["task_id"] == task_id:
                j = rework(j)
            js.append(j)

    with open(jsonl, "w") as f:
        for j in js:
            print(json.dumps(j, sort_keys=True), file=f, flush=True)


def convert(args):
    start: int = args.start
    count: int = args.count
    output: str = args.output

    hep = datasets.load_dataset(
        "bigcode/humanevalpack", "cpp", trust_remote_code=True
    )["test"]

    with open(output, "a") as out:
        gen_loop(out, hep, start, count)


def parse_args():
    parser = argparse.ArgumentParser()
    subp = parser.add_subparsers(
        title="mode",
        dest="mode",
        required=True,
        help="either 'convert' or 'fix'",
    )

    create_parser = subp.add_parser("convert")
    create_parser.add_argument(
        "output",
        type=str,
        help="Output jsonl file.",
    )
    create_parser.add_argument(
        "start",
        type=int,
        help="Start index of humanevalpack for generating data.",
    )
    create_parser.add_argument(
        "count", type=int, help="Number of tasks to convert from humanevalpack."
    )

    fix_parser = subp.add_parser("fix")
    fix_parser.add_argument(
        "jsonl",
        type=str,
        help="Input and output jsonl file.",
    )
    fix_parser.add_argument(
        "task_id",
        type=str,
        help="Task ID to fix in the jsonl.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.mode == "convert":
        convert(args)
    elif args.mode == "fix":
        fix(args)
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
