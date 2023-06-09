import abc
from abc import ABC
from logging import getLogger
from typing import List, Dict

from indexer_api.models import Token, TokenTransfer, FUNGIBLE_TOKENS
from .transfer_transactions import TransferTransaction
from web3.types import ChecksumAddress

logger = getLogger(__name__)


class AbstractStrategy(abc.ABC):
    strategy_params: Dict

    def __init__(self, strategy_params: Dict):
        self.strategy_params = strategy_params


class AbstractTransferStrategy(AbstractStrategy, abc.ABC):
    @abc.abstractmethod
    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        pass

    @staticmethod
    def _save_transfer_to_database(token: Token, transfer_transaction: TransferTransaction):
        token_transfer = transfer_transaction.to_token_transfer_model()
        if TokenTransfer.objects.filter(tx_hash=token_transfer.tx_hash).exists():
            logger.info(f"Transfer skipped: tx with hash {token_transfer.tx_hash} on token "
                        f"{token.name} (chain id: {token.network.chain_id}) already indexed")
        else:
            token_transfer.token_instance = token
            token_transfer.save()


class RecipientStrategy(AbstractTransferStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        if not (recipient := self.strategy_params.get("recipient")):
            raise ValueError("Strategy has no recipient provided. Please add recipient address to the strategy dict")
        transfers_with_recipient = list(filter(lambda tx: tx.recipient.lower() == recipient.lower(), transfer_transactions))
        logger.info(f"Found {len(transfers_with_recipient)} transfers of {token.name} with recipient {recipient}")
        for transfer_transaction in transfers_with_recipient:
            self._save_transfer_to_database(token, transfer_transaction)
        logger.info(f"Saved transfers to database")


class SenderStrategy(AbstractTransferStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        if not (sender := self.strategy_params.get("sender")):
            raise ValueError("Strategy has no sender provided. Please add sender address to the strategy dict")
        transfers_with_sender = list(filter(lambda tx: tx.sender.lower() == sender.lower(), transfer_transactions))
        logger.info(f"Found {len(transfers_with_sender)} transfers of {token.name} with sender {sender}")
        for transfer_transaction in transfers_with_sender:
            self._save_transfer_to_database(token, transfer_transaction)
        logger.info(f"Saved transfers to database")


class TokenScanStrategy(AbstractTransferStrategy):

    def start(self, token: Token, transfer_transactions: List[TransferTransaction]):
        logger.info(f"Found {len(transfer_transactions)} transfers of {token.name}")
        for transfer_transaction in transfer_transactions:
            self._save_transfer_to_database(token, transfer_transaction)
        logger.info(f"Saved transfers to database")


class AbstractBalanceStrategy(AbstractStrategy, ABC):

    @abc.abstractmethod
    def start(self, token: Token) -> List[ChecksumAddress]:
        raise NotImplementedError()


class SpecifiedHoldersStrategy(AbstractBalanceStrategy):
    def start(self, token: Token):
        if not (holders := self.strategy_params.get("holders")):
            raise ValueError("No holders specified. You need to set an array of holders which will be tracked")
        logger.info(f"Specified holders are {holders}")
        return holders


class TransfersParticipantsStrategy(AbstractBalanceStrategy):

    def start(self, token: Token) -> List[ChecksumAddress]:
        transfer_participant_pair = TokenTransfer.objects.filter(token_instance=token).values("sender",
                                                                                              "recipient").distinct()
        result = set()
        for pair in transfer_participant_pair:
            result.add(pair["sender"])
            result.add(pair["recipient"])
        logger.info(f"Found {len(result)} token transfer participants. Find their balances")
        return list(result)
