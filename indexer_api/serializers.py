from typing import Type

from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import IntegerField

from indexer_api.models import Network, Token, TokenBalance, Indexer


class TokenSerializer(ModelSerializer):
    network = IntegerField(source="network__chain_id")

    class Meta:
        model = Token
        fields = ["address", "name", "type", "strategy", "total_supply", "volume", "network"]


class NetworkSerializer(ModelSerializer):
    tokens = TokenSerializer(many=True)

    class Meta:
        model = Network
        fields = ["chain_id", "name", "rpc_url", "max_step", "type", "need_poa", "tokens"]


class TokenBalanceSerializer(ModelSerializer):
    class Meta:
        model = TokenBalance
        fields = "__all__"


class IndexerSerializer(ModelSerializer):
    class Meta:
        model = Indexer
        fields = "__all__"
