python manage.py collectstatic --noinput && \
python manage.py migrate && \
python create_super_user.py && \
gunicorn config.wsgi --bind 0.0.0.0:80
