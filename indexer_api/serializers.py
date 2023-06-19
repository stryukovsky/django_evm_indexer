from rest_framework.serializers import ModelSerializer, SerializerMethodField, CharField

from indexer_api.models import Network, Token, TokenBalance, Indexer, TokenTransfer, FUNGIBLE_TOKENS, \
    NON_FUNGIBLE_TOKENS, ERC1155_TOKENS


class NetworkSerializer(ModelSerializer):
    class Meta:
        model = Network
        fields = ["chain_id", "name", "rpc_url", "max_step", "type", "need_poa"]


class TokenSerializer(ModelSerializer):
    network = NetworkSerializer()

    class Meta:
        model = Token
        fields = ["address", "name", "type", "strategy", "total_supply", "volume", "network", ]


class TokenBalanceSerializer(ModelSerializer):
    class Meta:
        model = TokenBalance
        fields = "__all__"


class IndexerSerializer(ModelSerializer):
    watched_tokens = TokenSerializer(many=True)
    network = NetworkSerializer()

    class Meta:
        model = Indexer
        fields = ("name", "type", "strategy", "last_block", "short_sleep_seconds",
                  "long_sleep_seconds", "strategy_params", "network", "watched_tokens",)


class TokenTransferSerializer(ModelSerializer):
    token_transferred = SerializerMethodField(method_name="get_token_transferred")
    token = CharField(source="token_instance.address", allow_null=True)

    class Meta:
        model = TokenTransfer
        fields = ("sender", "recipient", "tx_hash", "token", "token_transferred")

    @staticmethod
    def get_token_transferred(instance: TokenTransfer):
        token_type = instance.token_instance.type
        result = {"type": token_type, "token": instance.token_instance.address}
        if token_type in FUNGIBLE_TOKENS:
            result["amount"] = str(instance.amount)

        elif token_type in NON_FUNGIBLE_TOKENS:
            result["token_id"] = str(instance.token_id)
        elif token_type in ERC1155_TOKENS:
            result["amount"] = str(instance.amount)
            result["token_id"] = str(instance.token_id)
        return result
