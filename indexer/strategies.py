import abc
from typing import List, Dict

from indexer_api.models import Token, TokenTransfer
from .transactions import TransferTransaction


class AbstractStrategy(abc.ABC):
    strategy_params: Dict
    token: Token

    def __init__(self, strategy_params: Dict):
        self.strategy_params = strategy_params

    @abc.abstractmethod
    def start(self, token: Token, token_transfers: List[TransferTransaction]):
        pass


class RecipientStrategy(AbstractStrategy):

    def start(self, token: Token, token_transfers: List[TransferTransaction]):
        recipient = self.strategy_params.get("recipient")
        if not recipient:
            raise ValueError("Strategy has no `recipient` provided. Please add recipient address to the strategy dict")
        for transfer in token_transfers:
            if transfer.recipient == recipient:
                print(str(transfer))


class SenderStrategy(AbstractStrategy):

    def start(self, token: Token, token_transfers: List[TransferTransaction]):
        if not (sender := self.strategy_params.get("sender")):
            raise ValueError("Strategy has no sender provided. Please add sender address to the strategy dict")
        for transfer in token_transfers:
            if transfer.sender == sender:
                print(str(transfer))


class TokenScanStrategy(AbstractStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        for transfer_transaction in transfer_transactions:
            token_transfer = transfer_transaction.to_model_instance()
            if not TokenTransfer.objects.filter(tx_hash=transfer_transaction.tx_hash).exists():
                token_transfer.token_instance = token
                token_transfer.save()


class TokenomicsStrategy(AbstractStrategy):

    def start(self, token: Token, token_transfer: List[TransferTransaction]):
        raise NotImplementedError
