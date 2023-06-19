from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from indexer_api.models import Network, Token, Indexer, TokenBalance, TokenType, TokenTransfer
from indexer_api.serializers import NetworkSerializer, TokenSerializer, IndexerSerializer, TokenTransferSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="List of **Networks** being indexed by **Indexers**",
    operation_id="List"
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Information on EVM **Network** used by **Indexers**",
    operation_id="Details"
))
class NetworkViewSet(ReadOnlyModelViewSet):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer

    lookup_field = "chain_id"
    ordering = ('-id',)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="List of **Tokens** being indexed by **Indexers**",
    operation_id="List"
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Information on **Token** used by **Indexers**",
    operation_id="Details"
))
class TokenViewSet(ReadOnlyModelViewSet):
    queryset = Token.objects.all()
    serializer_class = TokenSerializer
    search_fields = ("network__chain_id", "address",)
    ordering = ('-id',)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="List of **Indexers**",
    operation_id="List"
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Information on a single **Indexer**",
    operation_id="Details"
))
class IndexerViewSet(ReadOnlyModelViewSet):
    queryset = Indexer.objects.all()
    serializer_class = IndexerSerializer

    lookup_field = "name"
    search_fields = ("network__chain_id",)
    ordering = ('-id',)


class BalancesView(APIView):
    """
    Balances mainly are consist of
    - **holder** Ethereum address
    - their balance with either (or even both) **token_id** and **amount**
    """

    @staticmethod
    def get_nft_ids(balances: QuerySet) -> list[str]:
        result = []
        for balance in balances:
            if token_id := balance["token_id"]:
                result.append(str(token_id))
        return result

    @staticmethod
    def get_nft_amount(balances: QuerySet) -> str:
        if not balances:
            return "0"
        if not balances[0]["amount"]:
            return "0"
        return str(balances[0]["amount"])

    @staticmethod
    def get_fungible_amount(balances: QuerySet) -> str:
        if not balances:
            return "0"
        if not balances[0].get("amount"):
            return "0"
        return str(balances[0]["amount"])

    @staticmethod
    def get_generalized_balance(balances: QuerySet) -> dict:
        if not balances:
            return {}
        result = {}
        for balance in balances:
            token_id = str(balance["token_id"])
            amount = str(balance["amount"])
            result[token_id] = amount
        return result

    @swagger_auto_schema(operation_description="Get all listed tokens balance of **holder**",
                         operation_id="By holder", operation_summary="By holder")
    def get(self, request: Request, holder: str, format=None) -> Response:
        networks = Network.objects.all()
        response = {}
        for network in networks:
            chain_id = network.chain_id
            response[chain_id] = {}
            tokens = Token.objects.filter(network=network).all()
            for token in tokens:
                balances = TokenBalance.objects.filter(token_instance=token, holder__iexact=holder).values("token_id",
                                                                                                           "amount")
                token_type = token.type
                match token_type:
                    case TokenType.erc721enumerable:
                        value = self.get_nft_ids(balances)
                    case TokenType.erc721:
                        value = self.get_nft_amount(balances)
                    case TokenType.erc20:
                        value = self.get_fungible_amount(balances)
                    case TokenType.native:
                        value = self.get_fungible_amount(balances)
                    case _:
                        value = self.get_generalized_balance(balances)

                response[chain_id][token.address] = {
                    "token_type": token_type,
                    "balance": value
                }
        return Response(data=response)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="List of **Transfers**",
    operation_id="List"
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Details of a **Transfer**",
    operation_id="Details"
))
class TransfersViewSet(ReadOnlyModelViewSet):
    queryset = TokenTransfer.objects.all()
    serializer_class = TokenTransferSerializer
    search_fields = ('sender', 'recipient', 'token_instance__address')

    lookup_field = "tx_hash"
