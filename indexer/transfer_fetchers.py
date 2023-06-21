import abc
import json
from typing import List, Callable, Type, Dict, Sequence
from logging import getLogger
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractEvent
from web3.types import TxReceipt, TxParams

from indexer.transfer_transactions import (TransferTransaction,
                                           FungibleTransferTransaction,
                                           NonFungibleTransferTransaction,
                                           ERC1155TokenTransfer,
                                           NativeCurrencyTransferTransaction)
from indexer_api.models import Token, NetworkType, FUNGIBLE_TOKENS, NON_FUNGIBLE_TOKENS, ERC1155_TOKENS, TokenType

logger = getLogger(__name__)


class AbstractTransferFetcher(abc.ABC):
    token: Token
    w3: Web3

    def __init__(self, w3: Web3, token: Token):
        self.w3 = w3
        self.token = token

    @abc.abstractmethod
    def get_transfers(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        pass


class EventTransferFetcher(AbstractTransferFetcher):
    contract: Contract
    event: List[Type[ContractEvent]]
    get_events_function: Callable[[int, int], List[TransferTransaction]]
    token_action_type: Type[TransferTransaction]
    network_type: str

    def __init__(self, w3: Web3, token: Token, network_type: str):
        super().__init__(w3, token)
        abi = self._get_abi(token.type)
        address = token.address
        self.contract = self.w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)
        self.events = list(map(lambda event_name: self.contract.events[event_name], self._get_event_names(token.type)))
        self.network_type = network_type
        self.token_action_type = self._get_transfer_transaction_type(token.type)

    @staticmethod
    def _get_abi(token_type: str) -> List[Dict]:
        if token_type == TokenType.erc20:
            with open("indexer/abi/ERC20.json") as file:
                return json.load(file)
        # there is the same ABI for erc721 and erc721enumerable since both have the same Transfer event signature
        if token_type in [TokenType.erc721, TokenType.erc721enumerable]:
            with open("indexer/abi/ERC721.json") as file:
                return json.load(file)
        if token_type == TokenType.erc1155:
            with open("indexer/abi/ERC1155.json") as file:
                return json.load(file)
        raise ValueError(f"Unknown token type or token's ABI not provided in `abi` folder: {token_type}")

    @staticmethod
    def _get_event_names(token_type: str) -> List[str]:
        if token_type == TokenType.erc20:
            return ["Transfer"]
        if token_type in [TokenType.erc721, TokenType.erc721enumerable]:
            return ["Transfer"]
        if token_type == TokenType.erc1155:
            return ["TransferSingle", "TransferBatch"]
        raise ValueError(f"Unknown token type or type not implemented {token_type}")

    @staticmethod
    def _get_transfer_transaction_type(token_type: str) -> Type[TransferTransaction]:
        if token_type in FUNGIBLE_TOKENS:
            return FungibleTransferTransaction
        if token_type in NON_FUNGIBLE_TOKENS:
            return NonFungibleTransferTransaction
        if token_type in ERC1155_TOKENS:
            return ERC1155TokenTransfer

    def get_transfers(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        match self.network_type:
            case NetworkType.filterable:
                return self.__get_events_with_eth_filter(from_block, to_block)
            case NetworkType.no_filters:
                return self.__get_events_with_raw_filtering(from_block, to_block)
            case _:
                raise NotImplementedError(f"Network filtering type {self.network_type} not implemented yet")

    def __get_events_with_eth_filter(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        result = []
        for event in self.events:
            # noinspection PyUnresolvedReferences
            entries = event.create_filter(fromBlock=from_block, toBlock=to_block).get_all_entries()
            for entry in entries:
                token_actions = self.token_action_type.from_event_entry(entry)
                result.extend(token_actions)
        return result

    def __get_events_with_raw_filtering(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        events = self.contract.w3.eth.get_logs(
            {'fromBlock': from_block, 'toBlock': to_block, 'address': self.contract.address})
        result = []
        for event in events:
            result.extend(self.token_action_type.from_raw_log(event))
        return result

    def __str__(self):
        return f"Events of tokens {self.token.address} ({self.token.type}) " \
               f"on network {self.token.network.name} ({self.token.network.chain_id})"


class ReceiptTransferFetcher(AbstractTransferFetcher):
    def get_transfers(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        token_actions = []
        for block_number in range(from_block, to_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            logger.info(f"Taking receipts of block {block_number}")
            transactions: Sequence[TxParams] = block["transactions"]
            for transaction in transactions:
                try:
                    receipt: TxReceipt = self.w3.eth.get_transaction_receipt(transaction_hash=transaction["hash"])
                    if receipt["status"] != 0 and transaction["value"] != 0:
                        token_actions.append(
                            NativeCurrencyTransferTransaction(sender=receipt["from"], recipient=receipt["to"],
                                                              amount=transaction["value"],
                                                              tx_hash=transaction["hash"].hex()))
                        logger.info(f"Transaction {transaction['hash'].hex()} is added to list")
                    else:
                        logger.info(f"Transaction {transaction['hash'].hex()} is either failed or transfers no native")
                except Exception as e:
                    logger.info(f"Skip transaction {transaction['hash'].hex()} of block {block_number}: {e}")
        return token_actions

    def __str__(self):
        return f"Receipts of native currency on network {self.token.network.name} ({self.token.network.chain_id})"
