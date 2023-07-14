import abc
from logging import getLogger
from typing import List, Optional
from decimal import Decimal

from web3.contract import Contract
from web3.types import ChecksumAddress
from indexer_api.models import TokenBalance, Token
from web3 import Web3

logger = getLogger(__name__)


class AbstractBalanceCaller(abc.ABC):
    contract: Optional[Contract]
    token: Token

    def __init__(self, token: Token, contract: Optional[Contract]):
        self.contract = contract
        self.token = token

    @abc.abstractmethod
    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        raise NotImplementedError()


class NativeBalanceFetcher(AbstractBalanceCaller):
    w3: Web3

    def __init__(self, token: Token):
        super().__init__(token, None)
        self.w3 = Web3(Web3.HTTPProvider(token.network.rpc_url))

    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        balance, created = TokenBalance.objects.get_or_create(token_instance=self.token, holder=holder)
        if created:
            logger.info(f"Created a TokenBalance record of holder {holder} on token {self.token.name} (Native)")
        else:
            logger.info(
                f"TokenBalance record of holder {holder} on token {self.token.name} exists with amount: {balance.amount}")
        current_balance = self.w3.eth.get_balance(holder)
        if current_balance != balance.amount:
            logger.info(f"Balance of holder {holder} changed to {current_balance}")
            balance.amount = current_balance
            balance.save()
        else:
            logger.info(f"Balance of holder {holder} remains the same")
        return [balance]


class ContractBalanceFetcher(AbstractBalanceCaller, abc.ABC):
    contract: Contract

    def __init__(self, token: Token, contract: Optional[Contract]):
        if not contract:
            raise ValueError(f"ERC20BalanceCaller needs contract, not native currency")
        super().__init__(token, contract)


class ERC20BalanceCaller(ContractBalanceFetcher):

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


class ERC721BalanceCaller(ContractBalanceFetcher):

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


class ERC721EnumerableBalanceCaller(ContractBalanceFetcher):

    def get_balance(self, holder: ChecksumAddress) -> List[TokenBalance]:
        try:
            users_tokens_count: int = self.contract.functions.balanceOf(holder).call()
            current_tokens = set()
            tokens_already_held_queryset = TokenBalance.objects.filter(holder=holder, token_instance=self.token).values(
                "token_id")
            tokens_already_held = set()
            for token_balance in tokens_already_held_queryset:
                if token_id_already_held := token_balance.get("token_id"):
                    tokens_already_held.add(int(token_id_already_held))
            for i in range(users_tokens_count):
                token_id_already_held = self.contract.functions.tokenOfOwnerByIndex(holder, i).call()
                current_tokens.add(token_id_already_held)
            logger.info(f"Fetched {current_tokens} of holder {holder} on token {self.token.address}")
            tokens_to_be_removed = tokens_already_held.difference(current_tokens)
            tokens_to_be_added = current_tokens.difference(tokens_already_held)
            if not tokens_to_be_added and not tokens_to_be_added:
                logger.info(f"Skipped {holder} balance of token {self.token.address} remains to be {current_tokens}")
                return []
            for token_id_to_be_removed in tokens_to_be_removed:
                logger.info(f"Token {token_id_to_be_removed} was moved from {holder}. Delete a record in the database")
                TokenBalance.objects.filter(holder=holder, token_instance=self.token,
                                            token_id=Decimal(token_id_to_be_removed)).delete()
            for token_id_to_be_added in tokens_to_be_added:
                logger.info(f"Token {token_id_to_be_added} was given to {holder}. Create a record in the database")
                TokenBalance.objects.create(holder=holder,
                                            token_instance=self.token,
                                            token_id=token_id_to_be_added,
                                            amount=None)
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch balance of {holder} on {self.contract.address}: {e}")
            return []
