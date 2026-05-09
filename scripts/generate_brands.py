"""CLI skeleton for brand data generation.

P1: argument parsing + few-shot loading + Pydantic validation.
P3: actual LLM call (NotImplementedError for now).
"""

import argparse
import json
import sys
from pathlib import Path

# Derive project root from this script's location (scripts/ -> NourishFlow/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_BRANDS_DIR = PROJECT_ROOT / "backend" / "data" / "brands"

# Add backend to sys.path so we can import app.schemas.brand
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.schemas.brand import Brand  # noqa: E402


def load_few_shot(file_paths: list[str]) -> list[Brand]:
    """Load and validate few-shot example files into Brand objects."""
    brands: list[Brand] = []
    for raw_path in file_paths:
        p = Path(raw_path)
        if not p.exists():
            print(f"Error: few-shot file not found: {p}", file=sys.stderr)
            sys.exit(1)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            brand = Brand.model_validate(data)
            brands.append(brand)
        except Exception as e:
            print(
                f"Error: few-shot file {p.name} failed schema validation: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    return brands


def generate_brand_data(brand_name: str, few_shots: list[Brand], output_path: Path) -> None:
    """Generate brand data via LLM. TODO: P3 will implement LLM call."""
    raise NotImplementedError(
        "LLM generation not implemented in P1. "
        "Will be completed in P3 with litellm + few-shot prompting."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate brand nutrition data for NourishFlow."
    )
    parser.add_argument("--brand", required=True, help="Brand name to generate data for.")
    parser.add_argument(
        "--few-shot",
        default="",
        help="Comma-separated paths to few-shot JSON files for LLM context.",
    )
    parser.add_argument("--output", required=True, help="Output JSON file path.")

    args = parser.parse_args()

    DATA_BRANDS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Brand: {args.brand}")
    print(f"Output: {args.output}")

    few_shot_paths = [p.strip() for p in args.few_shot.split(",") if p.strip()]
    few_shots = load_few_shot(few_shot_paths)
    print(f"Loaded {len(few_shots)} few-shot examples: {[b.brand for b in few_shots]}")

    generate_brand_data(args.brand, few_shots, Path(args.output))


if __name__ == "__main__":
    main()
