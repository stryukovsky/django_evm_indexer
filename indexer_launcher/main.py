from docker import from_env

client = from_env()
client.containers.run("django_evm_indexer",
                      detach=True,
                      name="polygon-usdt-indexer",
                      command="python indexer/run.py",
                      environment=[
                          "INDEXER_NAME=polygon-usdt-indexer",
                          "POSTGRES_DB=django_evm_indexer",
                          "POSTGRES_USER=django_evm_indexer",
                          "POSTGRES_PASSWORD=qwerty12",
                          "POSTGRES_HOST=127.0.0.1",
                          "POSTGRES_PORT=5432",
                          "SUPERUSER_USERNAME=superuser",
                          "SUPERUSER_PASSWORD=superuser",
                      ])
