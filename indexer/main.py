import time
from typing import Dict, List

from web3 import Web3
from web3.middleware import geth_poa_middleware

from indexer.fetching_methods import ReceiptFetchingMethod
from indexer.strategies import AbstractStrategy, RecipientStrategy, SenderStrategy, TokenScanStrategy
from indexer_api.models import (
    Network,
    Token,
    Indexer)
from indexer_api.models import TokenStrategy, IndexerStrategy
from .fetching_methods import EventFetchingMethod, AbstractFetchingMethod


class Worker:
    indexer: Indexer
    network: Network
    w3: Web3
    fetching_methods: List[AbstractFetchingMethod]
    strategy: AbstractStrategy

    def __init__(self, indexer_name: str):
        self.indexer = Indexer.objects.get(name=indexer_name)
        self.network = self.indexer.network
        self.w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
        if self.network.need_poa:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.fetching_methods = self.build_fetch_methods(self.indexer.watched_tokens.all())
        self.strategy = self.build_strategy(self.indexer.strategy, self.indexer.strategy_params)

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
            for fetching_method in self.fetching_methods:
                token_transfers = fetching_method.get_token_actions(from_block, to_block)
                self.strategy.start(token_transfers)
                self.indexer.last_block = to_block
                self.indexer.save()
                time.sleep(self.indexer.short_sleep_seconds)

    def build_fetch_methods(self, tokens: List[Token]):
        self.fetching_methods = []
        for token in tokens:
            if token.strategy == TokenStrategy.event_based_transfer.value:
                self.fetching_methods.append(EventFetchingMethod(self.w3, token, self.network.type))
            if token.strategy == TokenStrategy.receipt_based_transfer.value:
                self.fetching_methods.append(ReceiptFetchingMethod(self.w3, token))
            else:
                raise ValueError(f"Not implemented {token.strategy}")

    def build_strategy(self, strategy: str, strategy_params: Dict):
        if strategy == IndexerStrategy.recipient.value:
            self.strategy = RecipientStrategy(strategy_params)
        if strategy == IndexerStrategy.sender.value:
            self.strategy = SenderStrategy(strategy_params)
        if strategy == IndexerStrategy.token_scan.value:
            self.strategy = TokenScanStrategy(strategy_params)
        else:
            raise ValueError(f"Not implemented strategy {strategy}")
