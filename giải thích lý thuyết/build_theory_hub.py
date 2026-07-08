from theory_hub import SiteGenerator
from theory_hub.config import OUTPUT_DIR


def main() -> None:
    theories = SiteGenerator().build()
    print(f"Đã sinh hub tại: {OUTPUT_DIR}")
    print(f"Tổng số bài: {len(theories)}")


if __name__ == "__main__":
    main()