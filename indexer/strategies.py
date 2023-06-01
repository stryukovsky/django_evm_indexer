import abc
from typing import List, Dict

from .transactions import TransferTransaction


class AbstractStrategy(abc.ABC):
    strategy_params: Dict

    def __init__(self, strategy_params: Dict):
        self.strategy_params = strategy_params

    @abc.abstractmethod
    def start(self, token_transfers: List[TransferTransaction]):
        pass


class RecipientStrategy(AbstractStrategy):

    def start(self, token_transfers: List[TransferTransaction]):
        recipient = self.strategy_params.get("recipient")
        if not recipient:
            raise ValueError("Strategy has no `recipient` provided. Please add recipient address to the strategy dict")
        for transfer in token_transfers:
            if transfer.recipient == recipient:
                print(str(transfer))


class SenderStrategy(AbstractStrategy):

    def start(self, token_transfers: List[TransferTransaction]):
        if not (sender := self.strategy_params.get("sender")):
            raise ValueError("Strategy has no sender provided. Please add sender address to the strategy dict")
        for transfer in token_transfers:
            if transfer.sender == sender:
                print(str(transfer))


class TokenScanStrategy(AbstractStrategy):

    def start(self, token_transfers: List[TransferTransaction]):
        for transfer in token_transfers:
            print(str(transfer))


class TokenomicsStrategy(AbstractStrategy):

    def start(self, token_transfer: List[TransferTransaction]):
        raise NotImplementedError
