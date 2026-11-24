from argparse import ArgumentParser

from goup.storage import DEFAULT_PATH
from goup.web import create_app


def main():
    parser = ArgumentParser(description="Run the local GoUp app.")
    parser.add_argument("--data", default=DEFAULT_PATH, help="Path to the local JSON data file")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    create_app(args.data).run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
