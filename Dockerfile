FROM python:3.10
WORKDIR /django_evm_indexer
ADD config ./config
ADD indexer_api ./indexer_api
ADD indexer ./indexer
ADD .gitignore ./.gitignore
ADD Dockerfile ./Dockerfile
ADD manage.py ./manage.py
ADD requirements.txt ./requirements.txt
ADD run_api.sh ./run_api.sh
ADD create_super_user.py ./create_super_user.py
RUN pip install -r requirements.txt
