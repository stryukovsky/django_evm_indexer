import abc
from typing import List, Dict

from indexer_api.models import Token, TokenTransfer, FUNGIBLE_TOKENS
from .transactions import TransferTransaction


class AbstractStrategy(abc.ABC):
    strategy_params: Dict

    def __init__(self, strategy_params: Dict):
        self.strategy_params = strategy_params

    @abc.abstractmethod
    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        pass

    @staticmethod
    def _save_transfer_to_database(token: Token, transfer_transaction: TransferTransaction):
        token_transfer = transfer_transaction.to_token_transfer_model()
        if not TokenTransfer.objects.filter(tx_hash=token_transfer.tx_hash).exists():
            token_transfer.token_instance = token
            token_transfer.save()


class RecipientStrategy(AbstractStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        recipient = self.strategy_params.get("recipient")
        if not recipient:
            raise ValueError("Strategy has no `recipient` provided. Please add recipient address to the strategy dict")
        for transfer_transaction in transfer_transactions:
            if transfer_transaction.recipient == recipient:
                self._save_transfer_to_database(token, transfer_transaction)


class SenderStrategy(AbstractStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        if not (sender := self.strategy_params.get("sender")):
            raise ValueError("Strategy has no sender provided. Please add sender address to the strategy dict")
        for transfer_transaction in transfer_transactions:
            if transfer_transaction.sender == sender:
                self._save_transfer_to_database(token, transfer_transaction)


class TokenScanStrategy(AbstractStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        for transfer_transaction in transfer_transactions:
            self._save_transfer_to_database(token, transfer_transaction)
