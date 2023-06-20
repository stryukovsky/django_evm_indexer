from django.urls import path
from explorer.views import index, transaction, token, holder, search, network

urlpatterns = [
    path("", index, name="explorer_index"),
    path("tx/<slug:tx>/", transaction, name="explorer_tx"),
    path("token/<int:token_id>/", token, name="explorer_token"),
    path("holder/<slug:address>/", holder, name="explorer_holder"),
    path("network/<int:chain_id>/", network, name="explorer_network"),
    path("search/", search, name="explorer_search")
]
