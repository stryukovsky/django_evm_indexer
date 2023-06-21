import os
from typing import Type, Optional, List, cast, Sequence, Union

from django.contrib import admin, messages
from django.contrib.admin import register
from django.db.models import QuerySet
from django.forms import ModelForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from docker import DockerClient
from docker import from_env
from prettyjson import PrettyJSONWidget

from indexer_api.models import Network, Indexer, Token, TokenBalance, TokenTransfer, IndexerStatus, TokenType, \
    FUNGIBLE_TOKENS, NON_FUNGIBLE_TOKENS

from logging import getLogger

logger = getLogger(__name__)


class ClientKeeper:
    client: Optional[DockerClient]

    def __init__(self):
        self.client = None

    def get_instance(self) -> DockerClient:
        if not self.client:
            self.client = from_env()
        return self.client


client_keeper = ClientKeeper()


def get_envs_for_indexer(indexer: str) -> List[str]:
    return [
        f"INDEXER_NAME={indexer}",
        f"SECRET_KEY={os.environ['SECRET_KEY']}",
        f"HOSTNAME={os.environ['HOSTNAME']}",
        f"POSTGRES_DB={os.environ['POSTGRES_DB']}",
        f"POSTGRES_USER={os.environ['POSTGRES_USER']}",
        f"POSTGRES_PASSWORD={os.environ['POSTGRES_PASSWORD']}",
        f"POSTGRES_HOST={os.environ['POSTGRES_HOST']}",
        f"POSTGRES_PORT={os.environ['POSTGRES_PORT']}",
    ]


@register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "chain_id", "rpc_url", "max_step", "type")


@admin.action(description="Create containers")
def create_containers(model_admin: admin.ModelAdmin, request, queryset: QuerySet[Indexer]):
    for indexer in queryset:
        try:
            client_keeper.get_instance().containers.run("django_evm_indexer",
                                                        detach=True,
                                                        name=indexer.name,
                                                        command="python indexer/run.py",
                                                        network="django_indexer_default",
                                                        environment=get_envs_for_indexer(indexer.name))
            model_admin.message_user(request, f"Successfully created container for {indexer.name}", messages.SUCCESS)
            indexer.status = IndexerStatus.on
            indexer.save()
        except Exception as e:
            model_admin.message_user(request, f"During creation of container for {indexer.name} error occurred {e}",
                                     messages.ERROR)


@admin.action(description="Restart containers")
def restart_containers(model_admin: admin.ModelAdmin, request, queryset: QuerySet[Indexer]):
    for indexer in queryset:
        try:
            container = client_keeper.get_instance().containers.get(indexer.name)
            container.remove(force=True)
            client_keeper.get_instance().containers.run("django_evm_indexer",
                                                        detach=True,
                                                        name=indexer.name,
                                                        command="python indexer/run.py",
                                                        network="django_indexer_default",
                                                        environment=get_envs_for_indexer(indexer.name))
            model_admin.message_user(request, f"Successfully restarted container for {indexer.name} indexer",
                                     messages.SUCCESS)
            indexer.status = IndexerStatus.on
            indexer.save()
        except Exception as e:
            model_admin.message_user(request, f"During restarting of container for {indexer.name}error occurred: {e}",
                                     messages.ERROR)


@admin.action(description="Remove containers")
def remove_containers(model_admin: admin.ModelAdmin, request, queryset: QuerySet[Indexer]):
    for indexer in queryset:
        try:
            container = client_keeper.get_instance().containers.get(indexer.name)
            container.remove(force=True)
            model_admin.message_user(request, f"Successfully removed container for {indexer.name} indexer",
                                     messages.SUCCESS)
            indexer.status = IndexerStatus.off
            indexer.save()
        except Exception as e:
            model_admin.message_user(request, f"During removing container for {indexer.name} error occurred: {e}",
                                     messages.ERROR)


class EditIndexerForm(ModelForm):
    class Meta:
        model = Indexer
        widgets = {
            "strategy_params": PrettyJSONWidget(),
        }
        fields = '__all__'


@register(Indexer)
class IndexerAdmin(admin.ModelAdmin):
    actions = [create_containers, restart_containers, remove_containers]

    readonly_fields = ('logs', "status")
    list_display = ("name", "status", "type", "network", "last_block", "strategy",)
    form = EditIndexerForm

    list_filter = ("network", "status")

    @admin.display(description="Logs")
    def logs(self, instance: Indexer) -> str:
        try:
            container = client_keeper.get_instance().containers.get(instance.name)
            log_entries = str(container.logs(tail=100).decode('utf-8')).replace("\n", "</code><br><code>")
            return format_html("<code>{}</code>", mark_safe(log_entries))
        except Exception as e:
            return f"Failed to fetch logs: {e}"


@register(TokenBalance)
class TokenBalanceAdmin(admin.ModelAdmin):
    readonly_fields = ("token_type",)

    list_filter = ("token_instance",)
    list_display = ("holder", "token_instance")

    search_fields = ("holder",)
    search_help_text = "Search by holders address"

    @admin.display(description="Token type")
    def token_type(self, instance: TokenBalance) -> str:
        return TokenType(instance.token_instance.type).label


@register(TokenTransfer)
class TokenTransferAdmin(admin.ModelAdmin):
    readonly_fields = ('token_type',)
    list_filter = ("token_instance",)
    list_display = ("id", "sender", "recipient", "token_instance", "transaction")

    search_fields = ("sender", "recipient", "tx_hash",)
    search_help_text = format_html("Search by <b>sender/recipient address</b> or <b>tx_hash</b>")

    @admin.display(description="Token type")
    def token_type(self, instance: TokenTransfer) -> str:
        return TokenType(instance.token_instance.type).label

    def transaction(self, instance: TokenTransfer) -> str:
        if explorer_url := instance.token_instance.network.explorer_url:
            return format_html(f"<a href='{explorer_url}/tx/{instance.tx_hash}'>{instance.tx_hash}</a>")
        else:
            return f"{instance.tx_hash}"

    def get_fieldsets(self, request, obj: Optional[TokenTransfer] = None):
        fieldsets = super(TokenTransferAdmin, self).get_fieldsets(request, obj)
        if not obj:
            return fieldsets
        fields = fieldsets[0][1]['fields']
        token: Token = cast(Token, obj.token_instance)
        token_type = token.type
        new_fields: List[Union[str, Sequence[str]]] = []
        for field in fields:
            if token_type in FUNGIBLE_TOKENS and field != "token_id":
                new_fields.append(field)
            if token_type in NON_FUNGIBLE_TOKENS and field != "amount":
                new_fields.append(field)
        fieldsets[0][1]['fields'] = new_fields
        return fieldsets


@register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "type", "network")
    list_filter = ("network", "type",)
