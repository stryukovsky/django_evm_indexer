import os
from typing import Type, Optional, List

from django.contrib import admin, messages
from django.contrib.admin import register
from django.db.models import QuerySet
from docker import DockerClient
from docker import from_env
from django.utils.html import format_html, mark_safe
from indexer_api.models import Network, Indexer, Token, TokenBalance, TokenTransfer, IndexerStatus, TokenType
from django.forms import ModelForm

from prettyjson import PrettyJSONWidget


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
    list_display = ("chain_id", "name", "rpc_url", "max_step", "type")


@admin.action(description="Create containers")
def create_containers(model_admin: Type["IndexerAdmin"], request, queryset: QuerySet[Indexer]):
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
def restart_containers(model_admin: Type["IndexerAdmin"], request, queryset: QuerySet[Indexer]):
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
def remove_containers(model_admin: Type["IndexerAdmin"], request, queryset: QuerySet[Indexer]):
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
    list_display = ("name", "status", "last_block", "network", "strategy", "type",)
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

    @admin.display(description="Token type")
    def token_type(self, instance: TokenBalance) -> str:
        return TokenType(instance.token_instance.type).label


@register(TokenTransfer)
class TokenTransferAdmin(admin.ModelAdmin):
    readonly_fields = ("token_type",)
    list_filter = ("token_instance",)
    list_display = ("sender", "recipient", "token_instance", "tx_hash")

    @admin.display(description="Token type")
    def token_type(self, instance: TokenTransfer) -> str:
        return TokenType(instance.token_instance.type).label


@register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "type", "network")
    list_filter = ("network", "type",)
