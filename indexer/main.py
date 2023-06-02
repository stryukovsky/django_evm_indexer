import time
from typing import Dict, List, Optional

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
from .transactions import TransferTransaction


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
        self.build_fetch_methods(self.indexer.watched_tokens.all())
        self.build_strategy(self.indexer.strategy, self.indexer.strategy_params)

    def cycle(self):
        while True:
            time.sleep(self.indexer.short_sleep_seconds)
            self.indexer.refresh_from_db()
            if (latest_block := self.get_latest_block()) is None:
                continue
            from_block = self.indexer.last_block
            to_block = min(from_block + self.network.max_step, latest_block)
            if from_block == to_block:
                print(f"No new blocks found, last block is {to_block}")
                time.sleep(self.indexer.long_sleep_seconds)
                continue
            print(f"Fetching transfers [{from_block}; {to_block}]")
            for fetching_method in self.fetching_methods:
                if transfers := self.fetch_transfers(fetching_method, from_block, to_block):
                    if self.handle_transfers(fetching_method, transfers):
                        self.increase_last_block(to_block)

    def get_latest_block(self) -> Optional[int]:
        try:
            return self.w3.eth.get_block("latest")["number"]
        except Exception as e:
            print(f"During fetching last block error occurred: {e}")
            return None

    def increase_last_block(self, to_block):
        self.indexer.last_block = to_block
        self.indexer.save()

    @staticmethod
    def fetch_transfers(fetching_method: AbstractFetchingMethod, from_block: int, to_block: int) -> \
            List[TransferTransaction]:
        try:
            return fetching_method.get_transactions(from_block, to_block)
        except Exception as e:
            print(f"During fetching {fetching_method} error occurred {e}")
            return []

    def handle_transfers(self, fetching_method: AbstractFetchingMethod, transfers: List[TransferTransaction]) -> bool:
        try:
            self.strategy.start(fetching_method.token, transfers)
            return True
        except Exception as e:
            print(f"During handling fetched transfers ({fetching_method}) error occurred {e}")
            return False

    def build_fetch_methods(self, tokens: List[Token]):
        self.fetching_methods = []
        for token in tokens:
            match token.strategy:
                case TokenStrategy.event_based_transfer.value:
                    self.fetching_methods.append(EventFetchingMethod(self.w3, token, self.network.type))
                case TokenStrategy.receipt_based_transfer.value:
                    self.fetching_methods.append(ReceiptFetchingMethod(self.w3, token))
                case _:
                    raise ValueError(f"Not implemented {token.strategy}")

    def build_strategy(self, strategy: str, strategy_params: Dict):
        match strategy:
            case IndexerStrategy.recipient.value:
                self.strategy = RecipientStrategy(strategy_params)
            case IndexerStrategy.sender.value:
                self.strategy = SenderStrategy(strategy_params)
            case IndexerStrategy.token_scan.value:
                self.strategy = TokenScanStrategy(strategy_params)
            case _:
                raise ValueError(f"Not implemented strategy {strategy}")
