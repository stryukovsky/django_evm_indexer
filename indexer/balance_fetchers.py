import abc
import json
import time
from typing import List, Dict, Optional

from web3 import Web3
from indexer_api.models import Token, Indexer
from indexer_api.models import TokenType
from web3.contract import Contract
from web3.types import ChecksumAddress
from .balance_callers import AbstractBalanceCaller, ERC20BalanceCaller, ERC721EnumerableBalanceCaller, \
    ERC721BalanceCaller


class AbstractBalanceFetcher(abc.ABC):
    indexer: Indexer
    contract: Optional[Contract]
    balance_caller: AbstractBalanceCaller

    def __init__(self, w3: Web3, token: Token, indexer: Indexer):
        self.w3 = w3
        self.token = token
        abi = self._get_abi(token.type)
        address = token.address
        if address:
            self.contract = self.w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)
        else:
            self.contract = None
        self.indexer = indexer
        self._build_balance_caller()

    @abc.abstractmethod
    def get_balances(self, holders: List[ChecksumAddress]):
        raise NotImplementedError()

    @staticmethod
    def _get_abi(token_type: str) -> List[Dict]:
        abi_filename: str
        match token_type:
            case TokenType.erc20:
                abi_filename = "indexer/abi/ERC20.json"
            case TokenType.erc721:
                abi_filename = "indexer/abi/ERC721.json"
            case TokenType.erc721enumerable:
                abi_filename = "indexer/abi/ERC721Enumerable.json"
            case TokenType.erc1155:
                abi_filename = "indexer/abi/ERC1155.json"
            case _:
                raise ValueError(f"Unknown token type or token's ABI not provided in `abi` folder: {token_type}")
        with open(abi_filename) as file:
            return json.load(file)

    def _build_balance_caller(self):
        match self.token.type:
            case TokenType.erc20:
                self.balance_caller = ERC20BalanceCaller(self.token, self.contract)
            case TokenType.erc721:
                self.balance_caller = ERC721BalanceCaller(self.token, self.contract)
            case TokenType.erc721enumerable:
                self.balance_caller = ERC721EnumerableBalanceCaller(self.token, self.contract)
            case TokenType.erc1155:
                raise NotImplementedError("Balance Fetcher: ERC1155 is not implemented yet")
            case TokenType.erc777:
                raise NotImplementedError("Balance Fetcher: ERC777 is not implemented yet")
            case _:
                raise ValueError(f"Unknown token type")


class SimpleBalanceFetcher(AbstractBalanceFetcher):
    def get_balances(self, holders: List[ChecksumAddress]):
        for holder in holders:
            balances = self.balance_caller.get_balance(holder)
            for balance in balances:
                balance.tracked_by = self.indexer
                balance.save()
                time.sleep(1)
