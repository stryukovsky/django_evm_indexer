import enum
import time
from typing import Dict, Optional

from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware

from indexer_api.models import (
    Network,
    Token,
    Indexer)
from indexer.fetching_methods import ReceiptFetchingMethod
from indexer.strategies import AbstractStrategy, RecipientStrategy, SenderStrategy, TokenScanStrategy
from .fetching_methods import EventFetchingMethod, AbstractFetchingMethod
from indexer_api.models import TokenStrategy, IndexerStrategy


class Worker:
    indexer: Indexer
    network: Network
    token: Token
    contract: Contract
    w3: Web3
    fetching_method: AbstractFetchingMethod
    strategy: AbstractStrategy

    def __init__(self, indexer_name: str, token_address: Optional[str], fetching_method: str, strategy: str,
                 strategy_params: dict):
        self.indexer = Indexer.objects.get(name=indexer_name)
        self.network = self.indexer.network
        self.w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
        self.token = Token.objects.get(address__iexact=token_address)
        if not self.token:
            raise ValueError(f"No token found with address {token_address}. Make sure you added it to database")
        if self.network.need_poa:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.fetching_method = self.build_token_action_method(fetching_method)
        self.strategy = self.build_strategy(strategy, strategy_params)

    def cycle(self):
        while True:
            self.indexer.refresh_from_db()
            latest_block = self.w3.eth.get_block("latest")["number"]
            from_block = self.indexer.last_block
            to_block = min(from_block + self.network.max_step, latest_block)
            if from_block == to_block:
                print(f"No new blocks found, last block is {to_block}")
                time.sleep(self.indexer.long_sleep_seconds)
                continue
            print(f"Fetching transfers [{from_block}; {to_block}]")
            token_transfers = self.fetching_method.get_token_actions(from_block, to_block)
            self.strategy.start(token_transfers)
            self.indexer.last_block = to_block
            self.indexer.save()
            time.sleep(self.indexer.short_sleep_seconds)

    def build_token_action_method(self, fetching_method: str) -> AbstractFetchingMethod:
        if fetching_method == TokenStrategy.event_based_transfer.value:
            return EventFetchingMethod(self.w3, self.token, self.network.type)
        if fetching_method == TokenStrategy.receipt_based_transfer.value:
            return ReceiptFetchingMethod(self.w3, self.token)
        raise ValueError(f"Not implemented {fetching_method}")

    @staticmethod
    def build_strategy(strategy: str, strategy_params: Dict) -> AbstractStrategy:
        if strategy == IndexerStrategy.recipient.value:
            return RecipientStrategy(strategy_params)
        if strategy == IndexerStrategy.sender.value:
            return SenderStrategy(strategy_params)
        if strategy == IndexerStrategy.token_scan.value:
            return TokenScanStrategy(strategy_params)
        raise ValueError(f"Not implemented strategy {strategy}")
