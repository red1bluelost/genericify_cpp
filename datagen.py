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

            while (resp := input(COMMANDS_MESSAGE).strip()) not in COMMANDS:
                pass
            match resp:
                case "exit":
                    return
                case "skip":
                    continue
                case _:
                    pass

            gdoc = dict(
                task_id=f"HEP/{idx}",
                base_prompt=read(base_prompt_path),
                sfinae_prompt=read(sfinae_prompt_path),
                concepts_prompt=read(concepts_prompt_path),
                starter_code=starter_code,
                base_canonical_solution=read(base_path),
                sfinae_canonical_solution=read(sfinae_path),
                concepts_canonical_solution=read(concepts_path),
                tests=read(tests_path),
                invalids=read(invalids_path),
            )
            print(json.dumps(gdoc, sort_keys=True), file=out, flush=True)
            print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output",
        type=str,
        help="Output jsonl file.",
    )
    parser.add_argument(
        "start",
        type=int,
        help="Start index of humanevalpack for generating data.",
    )
    parser.add_argument(
        "count", type=int, help="Number of tasks to convert from humanevalpack."
    )
    args = parser.parse_args()

    start: int = args.start
    count: int = args.count
    output: str = args.output

    hep = datasets.load_dataset(
        "bigcode/humanevalpack", "cpp", trust_remote_code=True
    )["test"]

    with open(output, "a") as out:
        gen_loop(out, hep, start, count)

    return 0


if __name__ == "__main__":
    sys.exit(main())
