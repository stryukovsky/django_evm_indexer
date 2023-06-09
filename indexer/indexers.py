import abc
import time
from logging import getLogger
from typing import Dict, List, Optional, Tuple

from web3 import Web3
from web3.middleware import geth_poa_middleware

from indexer.balance_fetchers import AbstractBalanceFetcher, SimpleBalanceFetcher
from indexer.strategies import (RecipientStrategy,
                                SenderStrategy,
                                TokenScanStrategy,
                                AbstractTransferStrategy,
                                SpecifiedHoldersStrategy,
                                AbstractStrategy,
                                AbstractBalanceStrategy,
                                TransfersParticipantsStrategy)
from indexer.transfer_fetchers import ReceiptTransferFetcher
from indexer_api.models import (
    Network,
    Token,
    Indexer, IndexerType)
from indexer_api.models import TokenStrategy, IndexerStrategy
from .transfer_fetchers import EventTransferFetched, AbstractTransferFetcher
from .transfer_transactions import TransferTransaction

logger = getLogger(__name__)


class AbstractIndexerWorker(abc.ABC):
    indexer: Indexer
    network: Network
    w3: Web3
    transfer_fetchers: List[AbstractTransferFetcher]
    strategy: AbstractStrategy

    def __init__(self, indexer: Indexer):
        self.indexer = indexer
        self.network = self.indexer.network
        self.w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
        if self.network.need_poa:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def cycle(self):
        while True:
            logger.info(f"Starting a cycle sleeping for {self.indexer.short_sleep_seconds} seconds")
            time.sleep(self.indexer.short_sleep_seconds)
            self.indexer.refresh_from_db()
            logger.info(f"Updating indexer data from database before start cycle main body")
            self._cycle_body()

    @abc.abstractmethod
    def _cycle_body(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def build_strategy(self, strategy: str, strategy_params: Dict):
        raise NotImplementedError()

    @abc.abstractmethod
    def build_fetchers(self, tokens: List[Token]):
        raise NotImplementedError()


class TransferIndexerWorker(AbstractIndexerWorker):
    strategy: AbstractTransferStrategy

    def __init__(self, indexer: Indexer):
        super().__init__(indexer)
        self.build_fetchers(self.indexer.watched_tokens.all())
        self.build_strategy(self.indexer.strategy, self.indexer.strategy_params)

    def _cycle_body(self):
        if (latest_block := self.get_latest_block()) is None:
            logger.info(f"Skip cycle since last block fetching failed")
            return
        from_block = self.indexer.last_block
        to_block = min(from_block + self.network.max_step, latest_block)
        if from_block == to_block:
            logger.info(f"No new blocks found, last block is {to_block}")
            time.sleep(self.indexer.long_sleep_seconds)
            return
        logger.info(f"Fetching transfers in blocks in the range [{from_block}; {to_block}]")
        for fetching_method in self.transfer_fetchers:
            transfers, error = self.fetch_transfers(fetching_method, from_block, to_block)
            if not error:
                logger.info(f"Fetched {len(transfers)} transfers")
                if transfers:
                    if self.handle_transfers(fetching_method, transfers):
                        logger.info(f"Transfers handled successfully. Increase last block")
                        self.increase_last_block(to_block)
                    else:
                        logger.info(f"Failed to handle transfers. Skip cycle and try again")
                else:
                    logger.info(f"No events found. Go to next blocks scope")
                    self.increase_last_block(to_block)
            else:
                logger.info(f"Failed to fetch transfers. Skip cycle and try again")

    def get_latest_block(self) -> Optional[int]:
        try:
            return self.w3.eth.get_block("latest")["number"]
        except Exception as e:
            logger.warning(f"During fetching last block error occurred: {e}")
            return None

    def increase_last_block(self, to_block):
        self.indexer.last_block = to_block
        self.indexer.save()

    @staticmethod
    def fetch_transfers(fetching_method: AbstractTransferFetcher, from_block: int, to_block: int) -> \
            Tuple[List[TransferTransaction], Optional[Exception]]:
        try:
            return fetching_method.get_transfers(from_block, to_block), None
        except Exception as e:
            logger.warning(f"During fetching {fetching_method} error occurred {e}")
            return [], e

    def handle_transfers(self, fetching_method: AbstractTransferFetcher, transfers: List[TransferTransaction]) -> bool:
        try:
            self.strategy.start(fetching_method.token, transfers)
            return True
        except Exception as e:
            logger.warning(f"During handling fetched transfers ({fetching_method}) error occurred {e}")
            return False

    def build_fetchers(self, tokens: List[Token]):
        self.transfer_fetchers = []
        for token in tokens:
            match token.strategy:
                case TokenStrategy.event_based_transfer.value:
                    self.transfer_fetchers.append(EventTransferFetched(self.w3, token, self.network.type))
                case TokenStrategy.receipt_based_transfer.value:
                    self.transfer_fetchers.append(ReceiptTransferFetcher(self.w3, token))
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
                raise ValueError(f"Not implemented strategy {strategy} for TransferIndexer. Change strategy in admin")


class BalanceIndexerWorker(AbstractIndexerWorker):
    strategy: AbstractBalanceStrategy
    balance_fetchers: List[AbstractBalanceFetcher]

    def __init__(self, indexer: Indexer):
        super().__init__(indexer)
        self.build_strategy(self.indexer.strategy, self.indexer.strategy_params)
        self.build_fetchers(self.indexer.watched_tokens.all())

    def build_strategy(self, strategy: str, strategy_params: Dict):
        match strategy:
            case IndexerStrategy.specified_holders.value:
                self.strategy = SpecifiedHoldersStrategy(strategy_params)
            case IndexerStrategy.transfers_participants.value:
                self.strategy = TransfersParticipantsStrategy(strategy_params)

    def build_fetchers(self, tokens: List[Token]):
        self.balance_fetchers = []
        for token in tokens:
            self.balance_fetchers.append(SimpleBalanceFetcher(self.w3, token))

    def _cycle_body(self):
        for balance_fetcher in self.balance_fetchers:
            holders = self.strategy.start(balance_fetcher.token)
            balance_fetcher.get_balances(holders)


class IndexerWorkerFactory:

    @staticmethod
    def build_indexer(indexer_name: str) -> AbstractIndexerWorker:
        indexer = Indexer.objects.get(name=indexer_name)
        match indexer.type:
            case IndexerType.transfer_indexer:
                return TransferIndexerWorker(indexer)
            case IndexerType.balance_indexer:
                return BalanceIndexerWorker(indexer)
            case _:
                raise NotImplementedError(f"Indexer of type {indexer.type} not impelemting")
