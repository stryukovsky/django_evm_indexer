import abc
from logging import getLogger
from typing import List

from web3.contract import Contract
from web3.types import ChecksumAddress
from indexer_api.models import TokenBalance, Token

logger = getLogger(__name__)


class AbstractBalanceCaller(abc.ABC):
    contract: Contract
    token: Token

    def __init__(self, token: Token, contract: Contract):
        self.contract = contract
        self.token = token

    @abc.abstractmethod
    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        raise NotImplementedError()


class ERC20BalanceCaller(AbstractBalanceCaller):

    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        try:
            result: int = self.contract.functions.balanceOf(holder).call()
            logger.info(f"Fetched {result} of holder {holder} on token {self.token.address}")
            token_balance, created = TokenBalance.objects.get_or_create(token_instance=self.token, holder=holder)
            if created:
                logger.info(f"Created a TokenBalance record of holder {holder} on token {self.token.address} (ERC20)")
            else:
                logger.info(f"Holder {holder} already owned {self.token.address} with amount of {token_balance.amount}")
            if token_balance.amount != result:
                token_balance.amount = result
                logger.info(f"Holder {holder} balance of token {self.token.address} set to {result}")
                return [token_balance]
            else:
                logger.info(f"Skipped {holder} balance of token {self.token.address} remains to be {result}")
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch balance of {holder} on {self.contract.address}: {e}")
            return []


class ERC721BalanceCaller(AbstractBalanceCaller):

    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        try:
            result: int = self.contract.functions.balanceOf(holder).call()
            logger.info(f"Fetched {result} NFTs of holder {holder} on token {self.token.address}")
            token_balance, created = TokenBalance.objects.get_or_create(token_instance=self.token, holder=holder)
            if created:
                logger.info(f"Created a TokenBalance record of holder {holder} on NFT token {self.token.address}")
            else:
                logger.info(f"Holder {holder} already owned NFT {self.token.address} of {token_balance.amount} tokens")
            if token_balance.amount != result:
                token_balance.amount = result
                logger.info(f"Holder {holder} balance of token {self.token.address} set to {result}")
                return [token_balance]
            else:
                logger.info(f"Skipped {holder} balance of token {self.token.address} remains to be {result}")
                return []
        except Exception as e:
            logger.warning(f"Failed to fetch balance of {holder} on {self.contract.address}: {e}")
            return []


class ERC721EnumerableBalanceCaller(AbstractBalanceCaller):

    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        try:
            users_tokens_count: int = self.contract.functions.balanceOf(holder).call()
            current_tokens = set()
            tokens_already_held_queryset = TokenBalance.objects.filter(holder=holder, token_instance=self.token).values(
                "token_id")
            tokens_already_held = set(map(lambda token: int(token['token_id']), tokens_already_held_queryset))
            for i in range(users_tokens_count):
                token_id = self.contract.functions.tokenOfOwnerByIndex(holder, i).call()
                current_tokens.add(token_id)
            logger.info(f"Fetched {current_tokens} of holder {holder} on token {self.token.address}")
            tokens_to_be_removed = tokens_already_held.difference(current_tokens)
            tokens_to_be_added = current_tokens.difference(tokens_already_held)
            if not tokens_to_be_added and not tokens_to_be_added:
                logger.info(f"Skipped {holder} balance of token {self.token.address} remains to be {current_tokens}")
                return []
            for token_id in tokens_to_be_removed:
                logger.info(f"Token {token_id} was moved from {holder}. Delete a record in the database")
                TokenBalance.objects.filter(holder=holder, token_instance=self.token, token_id=token_id).delete()
            for token_id in tokens_to_be_added:
                logger.info(f"Token {token_id} was given to {holder}. Create a record in the database")
                TokenBalance.objects.create(holder=holder,
                                            token_instance=self.token,
                                            token_id=token_id,
                                            amount=None)
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch balance of {holder} on {self.contract.address}: {e}")
            return []
