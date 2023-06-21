from typing import Dict, Union, List

from django.db.models import QuerySet

from indexer_api.models import TokenBalance, Token, Network, TokenType


class Balances:
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

    @staticmethod
    def get_balances(holder: str, verbose: bool = False) -> Dict:
        networks = Network.objects.all()
        result: Dict[Union[str, int], Dict] = {}
        for network in networks:
            network_identifier: Union[str, int] = network.chain_id
            if verbose:
                network_identifier = network.name
            result[network_identifier] = {}
            tokens = Token.objects.filter(network=network).all()
            for token in tokens:
                balances = TokenBalance.objects.filter(token_instance=token, holder__iexact=holder).values("token_id",
                                                                                                           "amount")
                token_type = token.type
                value: Union[str, List[str], Dict[str, str]]
                match token_type:
                    case TokenType.erc721enumerable:
                        value = Balances.get_nft_ids(balances)
                    case TokenType.erc721:
                        value = Balances.get_nft_amount(balances)
                    case TokenType.erc20:
                        value = Balances.get_fungible_amount(balances)
                    case TokenType.native:
                        value = Balances.get_fungible_amount(balances)
                    case _:
                        value = Balances.get_generalized_balance(balances)

                result[network_identifier][token.address] = {
                    "token_type": token_type,
                    "balance": value
                }
                if verbose:
                    result[network_identifier][token.address]["token_name"] = token.name
        return result
