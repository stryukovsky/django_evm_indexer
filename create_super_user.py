import os
import sys
import django

django_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(django_dir)
sys.path.append(django_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

SUPERUSER_USERNAME = os.environ["SUPERUSER_USERNAME"]
SUPERUSER_PASSWORD = os.environ["SUPERUSER_PASSWORD"]

from django.contrib.auth.models import User


def main():
    if User.objects.filter(username=SUPERUSER_USERNAME).exists():
        print("Superuser already exists")
    else:
        User.objects.create_superuser(username=SUPERUSER_USERNAME, password=SUPERUSER_PASSWORD)
        print("Created superuser")


if __name__ == '__main__':
    main()
