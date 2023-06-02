import os
from typing import Type

from django.contrib import admin
from django.db.models import QuerySet
from django.contrib.admin import register
from indexer_api.models import Network, Indexer, Token, TokenBalance, TokenTransfer
from django.conf import settings

from docker import from_env

client = from_env()


@register(Network)
class NetworkAdmin(admin.ModelAdmin):
    pass


@admin.action(description="Turn ON indexer(s)")
def turn_on_indexers(model_admin: Type["IndexerAdmin"], request, queryset: QuerySet[Indexer]):
    for indexer in queryset:
        client.containers.run("django_evm_indexer",
                              detach=True,
                              name=indexer.name,
                              command="python indexer/run.py",
                              environment=[
                                  f"INDEXER_NAME={indexer.name}",
                                  f"POSTGRES_DB={os.environ['POSTGRES_DB']}",
                                  f"POSTGRES_USER={os.environ['POSTGRES_USER']}",
                                  f"POSTGRES_PASSWORD={os.environ['POSTGRES_PASSWORD']}",
                                  f"POSTGRES_HOST={os.environ['POSTGRES_HOST']}",
                                  f"POSTGRES_PORT={os.environ['POSTGRES_PORT']}",
                              ])


@admin.action(description="Turn OFF indexer(s)")
def turn_off_indexers(modeladmin, request, queryset):
    for indexer in queryset:
        client.containers.remove(indexer.name, force=True)


@register(Indexer)
class IndexerAdmin(admin.ModelAdmin):
    actions = [turn_on_indexers, turn_off_indexers]


@register(Token)
class TokenAdmin(admin.ModelAdmin):
    pass


@register(TokenBalance)
class TokenBalanceAdmin(admin.ModelAdmin):
    pass


@register(TokenTransfer)
class TokenTransferAdmin(admin.ModelAdmin):
    pass
