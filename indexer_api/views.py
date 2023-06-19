from django.db.models import QuerySet
from django.http.response import HttpResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from indexer_api.balances import Balances
from indexer_api.metrics import IndexerMetrics
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

    @swagger_auto_schema(operation_description="Get all listed tokens balance of **holder**",
                         operation_id="By holder", operation_summary="By holder")
    def get(self, request: Request, holder: str, format=None) -> Response:
        return Response(data=Balances.get_balances(holder))


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


class IndexerMetricsView(APIView):

    def get(self, request: Request):
        return HttpResponse(content=IndexerMetrics().to_prometheus_metrics(), content_type="text/plain")
