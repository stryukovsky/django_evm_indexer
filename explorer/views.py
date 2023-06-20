from django.http.request import HttpRequest
from django.http.response import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect

from indexer_api.balances import Balances
from indexer_api.metrics import IndexerMetrics
from indexer_api.models import TokenTransfer, TokenType, Token, TokenBalance, Network
from indexer_api.validators import is_ethereum_address_valid


def index(request: HttpRequest) -> HttpResponse:
    context = {
        "last_transfers": TokenTransfer.objects.order_by("-id").all()[:10],
        "metrics": IndexerMetrics().to_django_template_dict(),
        "networks": Network.objects.all(),
    }
    return render(request, "explorer/explorer.html", context)


def _get_pretty_transfer(transfer: TokenTransfer) -> str:
    match transfer.token_instance.type:
        case TokenType.native:
            return f"{transfer.amount} native currency"
        case TokenType.erc20:
            return f"{transfer.amount} tokens"
        case TokenType.erc721enumerable:
            return f"NFT with ID {transfer.token_id}"
        case TokenType.erc721:
            return f"NFT with ID {transfer.token_id}"
        case TokenType.erc1155:
            return f"{transfer.amount} tokens of ID {transfer.token_id}"
        case _:
            raise NotImplementedError(f"Type {transfer.token_instance.type} is not implemented")


def transaction(request: HttpRequest, tx: str) -> HttpResponse:
    transaction_instance = get_object_or_404(TokenTransfer, tx_hash=tx)
    context = {
        "tx": transaction_instance,
        "pretty_transfer": _get_pretty_transfer(transaction_instance),
    }
    return render(request, "explorer/transaction.html", context)


def token(request: HttpRequest, token_id: int) -> HttpResponse:
    instance = get_object_or_404(Token, id=token_id)
    context = {
        "token": instance,
        "last_transfers": TokenTransfer.objects.filter(token_instance=instance).order_by("-id").all()[:10]
    }
    return render(request, "explorer/token.html", context=context)


def holder(request: HttpRequest, address: str) -> HttpResponse:
    if not is_ethereum_address_valid(address):
        raise Http404()
    context = {
        "address": address,
        "balances": Balances.get_balances(address, verbose=True)
    }
    return render(request, "explorer/holder.html", context=context)


def network(request: HttpRequest, chain_id: int) -> HttpResponse:
    network_instance = get_object_or_404(Network, chain_id=chain_id)
    last_transfers = TokenTransfer.objects.filter(token_instance__network=network_instance).order_by("-id").all()[:10]
    context = {
        "network": network_instance,
        "last_transfers": last_transfers,
    }
    return render(request, "explorer/network.html", context=context)


def search(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("/admin/explorer/")
    if not (query := request.POST.get("query")):
        return redirect("/admin/explorer/")
    query = str(query).strip()
    if transfer := TokenTransfer.objects.filter(tx_hash__iexact=query).first():
        return redirect(f"/admin/explorer/tx/{transfer.tx_hash}/")
    if token_instances := Token.objects.filter(address__iexact=query).all():
        if len(token_instances) == 1:
            return redirect(f"/admin/explorer/token/{token_instances[0].id}/")
        else:
            return render(request, "explorer/search_results.html", context={"query": query, "results": token_instances})
    if token_instances := Token.objects.filter(name__iexact=query).all():
        if len(token_instances) == 1:
            return redirect(f"/admin/explorer/token/{token_instances[0].id}/")
        else:
            return render(request, "explorer/search_results.html", context={"query": query, "results": token_instances})
    if is_ethereum_address_valid(query):
        return redirect(f"/admin/explorer/holder/{query}/")
    else:
        return render(request, "explorer/not_found.html")


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "explorer/not_found.html")
