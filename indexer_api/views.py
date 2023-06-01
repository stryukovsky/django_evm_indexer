from rest_framework.viewsets import ModelViewSet
from indexer_api.models import Network, Token, Indexer
from indexer_api.serializers import NetworkSerializer, TokenSerializer, IndexerSerializer


class NetworkViewSet(ModelViewSet):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer


class TokenViewSet(ModelViewSet):
    queryset = Token.objects.all()
    serializer_class = TokenSerializer


class IndexerViewSet(ModelViewSet):
    queryset = Indexer.objects.all()
    serializer_class = IndexerSerializer
