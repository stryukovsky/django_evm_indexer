from rest_framework.routers import DefaultRouter
from indexer_api.views import NetworkViewSet, TokenViewSet, IndexerViewSet

router = DefaultRouter()
router.register("networks", NetworkViewSet)
router.register("tokens", TokenViewSet)
router.register("indexers", IndexerViewSet)

urlpatterns = router.urls
