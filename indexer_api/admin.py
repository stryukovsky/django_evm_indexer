from django.contrib import admin
from django.contrib.admin import register
from indexer_api.models import Network, Indexer, Token, TokenBalance


@register(Network)
class NetworkAdmin(admin.ModelAdmin):
    pass


@register(Indexer)
class IndexerAdmin(admin.ModelAdmin):
    pass


@register(Token)
class TokenAdmin(admin.ModelAdmin):
    pass


@register(TokenBalance)
class TokenBalanceAdmin(admin.ModelAdmin):
    pass
