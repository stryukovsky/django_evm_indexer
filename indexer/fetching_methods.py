import abc
import json
from typing import List, Callable, Type, Dict, Sequence

from web3 import Web3
from web3.contract import Contract
from web3.contract.base_contract import BaseContractEvent
from web3.types import TxReceipt, TxParams

from indexer.token_actions import (TokenTransfer,
                                   FungibleTokenTransfer,
                                   NonFungibleTokenTransfer,
                                   ERC1155TokenTransfer,
                                   NativeCurrencyTransfer)
from indexer_api.models import Token, NetworkType, FUNGIBLE_TOKENS, NON_FUNGIBLE_TOKENS, ERC1155_TOKENS, TokenType


class AbstractFetchingMethod(abc.ABC):
    token: Token
    w3: Web3

    def __init__(self, w3: Web3, token: Token):
        self.w3 = w3
        self.token = token

    @abc.abstractmethod
    def get_token_actions(self, from_block: int, to_block: int) -> List[TokenTransfer]:
        pass


class EventFetchingMethod(AbstractFetchingMethod):
    contract: Contract
    event: List[Type[BaseContractEvent]]
    get_events_function: Callable[[int, int], List[TokenTransfer]]
    token_action_type: Type[TokenTransfer]
    network_type: str

    def __init__(self, w3: Web3, token: Token, network_type: str):
        super().__init__(w3, token)
        abi = self._get_abi(token.type)
        address = token.address
        self.contract = self.w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)
        self.events = list(map(lambda event_name: self.contract.events[event_name], self._get_event_names(token.type)))
        self.network_type = network_type
        self.token_action_type = self._get_token_action(token.type)

    @staticmethod
    def _get_abi(token_type: str) -> List[Dict]:
        if token_type == TokenType.erc20:
            with open("abi/ERC20.json") as file:
                return json.load(file)
        if token_type == TokenType.erc721:
            with open("abi/ERC721.json") as file:
                return json.load(file)
        if token_type == TokenType.erc1155:
            with open("abi/ERC1155.json") as file:
                return json.load(file)
        raise ValueError(f"Unknown token type or token's ABI not provided in `abi` folder: {token_type}")

    @staticmethod
    def _get_event_names(token_type: str) -> List[str]:
        if token_type == TokenType.erc20:
            return ["Transfer"]
        if token_type == TokenType.erc721:
            return ["Transfer"]
        if token_type == TokenType.erc1155:
            return ["TransferSingle", "TransferBatch"]
        raise ValueError(f"Unknown token type or type not implemented {token_type}")

    @staticmethod
    def _get_token_action(token_type: str) -> Type[TokenTransfer]:
        if token_type in FUNGIBLE_TOKENS:
            return FungibleTokenTransfer
        if token_type in NON_FUNGIBLE_TOKENS:
            return NonFungibleTokenTransfer
        if token_type in ERC1155_TOKENS:
            return ERC1155TokenTransfer

    def get_token_actions(self, from_block: int, to_block: int) -> List[TokenTransfer]:
        if self.network_type == NetworkType.filterable:
            return self.__get_events_with_eth_filter(from_block, to_block)
        else:
            return self.__get_events_with_raw_filtering(from_block, to_block)

    def __get_events_with_eth_filter(self, from_block: int, to_block: int) -> List[TokenTransfer]:
        result = []
        for event in self.events:
            entries = event.create_filter(fromBlock=from_block, toBlock=to_block).get_all_entries()
            for entry in entries:
                token_actions = self.token_action_type.from_event_entry(entry)
                result.extend(token_actions)
        return result

    def __get_events_with_raw_filtering(self, from_block: int, to_block: int) -> List[TokenTransfer]:
        events = self.contract.w3.eth.get_logs(
            {'fromBlock': from_block, 'toBlock': to_block, 'address': self.contract.address})
        result = []
        for event in events:
            result.extend(self.token_action_type.from_raw_log(event))
        return result


class ReceiptFetchingMethod(AbstractFetchingMethod):
    def get_token_actions(self, from_block: int, to_block: int) -> List[TokenTransfer]:
        token_actions = []
        for block_number in range(from_block, to_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            print(f"Taking receipts of block {block_number}")
            transactions: Sequence[TxParams] = block["transactions"]
            for transaction in transactions:
                try:
                    receipt: TxReceipt = self.w3.eth.get_transaction_receipt(transaction_hash=transaction["hash"])
                    if receipt["status"] != 0 and transaction["value"] != 0:
                        token_actions.append(NativeCurrencyTransfer(sender=receipt["from"], recipient=receipt["to"],
                                                                    amount=transaction["value"],
                                                                    tx_hash=transaction["hash"].hex()))
                        print(f"Transaction {transaction['hash'].hex()} is added to list")
                    else:
                        print(f"Transaction {transaction['hash'].hex()} is either failed or transfers no native")
                except Exception as e:
                    print(f"Skip transaction {transaction['hash'].hex()} of block {block_number}: {e}")
        return token_actions
