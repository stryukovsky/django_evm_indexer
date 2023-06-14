from rest_framework.routers import SimpleRouter, Route, DynamicRoute
from indexer_api.views import NetworkViewSet, TokenViewSet, IndexerViewSet, BalancesView, TransfersViewSet
from django.urls import path, re_path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

router = SimpleRouter()
router.register("networks", NetworkViewSet)
router.register("tokens", TokenViewSet)
router.register("indexers", IndexerViewSet)
router.register("transfers", TransfersViewSet, basename="transfers")

schema_view = get_schema_view(
    openapi.Info(
        title="EVM Indexer",
        default_version='v1',
        description="This API allows to get access to both administrative and indexed data through REST API interactions."
    ),
    public=True,
    permission_classes=[permissions.IsAdminUser],
)
urlpatterns = [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('docs/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('balances/holder/<slug:holder>', BalancesView.as_view(), name="Balances"),
]

urlpatterns += router.urls
