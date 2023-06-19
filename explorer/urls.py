from django.urls import path
from explorer.views import index, transaction, token, holder, search

urlpatterns = [
    path("", index),
    path("tx/<slug:tx>/", transaction),
    path("token/<int:token_id>/", token),
    path("holder/<slug:address>/", holder),
    path("search/", search)
]
