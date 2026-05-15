import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from gwisp.ui.sync_ocr_app import main as run_app

    run_app()


if __name__ == "__main__":
    main()
