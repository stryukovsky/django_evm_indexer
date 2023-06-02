import os
import sys

import django

django_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(django_dir)
sys.path.append(django_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

INDEXER_NAME = os.environ["INDEXER_NAME"]

from indexer.main import Worker


def main():
    Worker(INDEXER_NAME).cycle()


if __name__ == "__main__":
    main()
