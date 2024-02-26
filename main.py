import argparse
import dataclasses
import sys

from typing import Optional


@dataclasses.dataclass
class Arguments:
    """
    Program arguments
    """

    clang_path: str
    limit: Optional[int]
    max_length_generation: int
    model: str
    n_samples: int
    precision: str
    temperature: float


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--clang_path",
        required=True,
        type=str,
        help="Path to recent clang++ compiler",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of samples to solve and evaluate from the benchmark",
    )
    parser.add_argument(
        "--max_length_generation",
        type=int,
        default=512,
        help="Maximum length of generated sequence (prompt+generation)",
    )
    parser.add_argument(
        "--model",
        required=True,
        type=str,
        help="Model to evaluate, provide a repo name in Hugging Face hub or a local path",
    )
    parser.add_argument(
        "--n_samples",
        required=True,
        type=int,
        help="Number of completions to generate for each sample.",
    )
    parser.add_argument(
        "--precision",
        type=str,
        default="fp32",
        choices=["fp32", "fp16", "bf16"],
        help="Model precision, from: fp32, fp16 or bf16",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature used for generation.",
    )

    args = parser.parse_args()

    return Arguments(
        clang_path=args.clang_path,
        limit=args.limit,
        max_length_generation=args.max_length_generation,
        model=args.model,
        n_samples=args.n_samples,
        precision=args.precision,
        temperature=args.temperature,
    )


def main() -> int:
    args: Arguments = parse_args()
    print(f"hello world {args}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
