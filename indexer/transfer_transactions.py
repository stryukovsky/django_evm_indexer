import abc
import dataclasses
from logging import getLogger
from typing import Dict, List, Tuple, Sequence

from web3 import Web3
from web3.types import ChecksumAddress, HexStr, HexBytes, LogReceipt

from indexer_api.models import TokenTransfer
from web3.datastructures import AttributeDict
from .utils import AbiDecoder

logger = getLogger(__name__)


@dataclasses.dataclass
class TransferTransaction(abc.ABC):
    sender: ChecksumAddress
    recipient: ChecksumAddress
    tx_hash: HexStr

    @staticmethod
    @abc.abstractmethod
    def from_event_entry(event_entry: AttributeDict) -> List["TransferTransaction"]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def from_raw_log(cls, event: LogReceipt) -> List["TransferTransaction"]:
        raise NotImplementedError()

    @abc.abstractmethod
    def to_token_transfer_model(self) -> TokenTransfer:
        pass


@dataclasses.dataclass
class NativeCurrencyTransferTransaction(TransferTransaction):
    token = None

    def to_token_transfer_model(self) -> TokenTransfer:
        token_transfer = TokenTransfer()
        token_transfer.amount = self.amount
        token_transfer.sender = self.sender
        token_transfer.recipient = self.recipient
        token_transfer.token_id = None
        token_transfer.tx_hash = self.tx_hash
        return token_transfer

    amount: int

    @staticmethod
    def from_event_entry(event_entry: AttributeDict) -> List["TransferTransaction"]:
        raise NotImplementedError("It is impossible to handle native currency transfer, use receipt-based way")

    @classmethod
    def from_raw_log(cls, event: LogReceipt) -> List["TransferTransaction"]:
        raise NotImplementedError("It is impossible to handle native currency transfer, use receipt-based way")


@dataclasses.dataclass
class FungibleTransferTransaction(TransferTransaction):
    event_hash = Web3.keccak(text="Transfer(address,address,uint256)")
    amount: int

    def to_token_transfer_model(self) -> TokenTransfer:
        model_instance = TokenTransfer()
        model_instance.amount = self.amount
        model_instance.sender = self.sender
        model_instance.recipient = self.recipient
        model_instance.token_id = None
        model_instance.tx_hash = self.tx_hash
        return model_instance

    @classmethod
    def from_raw_log(cls, event: LogReceipt) -> List["TransferTransaction"]:
        if len(event["topics"]) not in (3, 4):
            return []
        if event["topics"][0] != cls.event_hash:
            return []
        sender = AbiDecoder.bytes32_to_address(event["topics"][1])
        recipient = AbiDecoder.bytes32_to_address(event["topics"][2])
        tx_hash = HexStr(event["transactionHash"].hex())
        if len(event["topics"]) == 4:
            amount = AbiDecoder.bytes32_to_uint256(event["topics"][3])
        else:
            amount = AbiDecoder.bytes32_to_uint256(HexBytes(event["data"]))
        return [
            FungibleTransferTransaction(
                sender=sender,
                recipient=recipient,
                tx_hash=tx_hash,
                amount=amount
            )
        ]

    @staticmethod
    def from_event_entry(event_entry: AttributeDict) -> List["TransferTransaction"]:
        return [FungibleTransferTransaction(
            sender=event_entry["args"]["from"],
            recipient=event_entry["args"]["to"],
            tx_hash=event_entry["transactionHash"].hex(),
            amount=event_entry["args"]["value"])]

    def __str__(self):
        return f"Tokens {self.amount} sent {self.sender} -> {self.recipient}"


@dataclasses.dataclass
class NonFungibleTransferTransaction(TransferTransaction):
    event_hash = Web3.keccak(text="Transfer(address,address,uint256)")
    token_id: int

    def to_token_transfer_model(self) -> TokenTransfer:
        model_instance = TokenTransfer()
        model_instance.amount = None
        model_instance.sender = self.sender
        model_instance.recipient = self.recipient
        model_instance.token_id = self.token_id
        model_instance.tx_hash = self.tx_hash
        return model_instance

    @classmethod
    def from_raw_log(cls, event: LogReceipt) -> List["TransferTransaction"]:
        if len(event["topics"]) not in (3, 4):
            return []
        if event["topics"][0] != cls.event_hash:
            return []
        if len(event["topics"]) == 4:
            token_id = AbiDecoder.bytes32_to_uint256(event["topics"][3])
        else:
            token_id = AbiDecoder.bytes32_to_uint256(HexBytes(event["data"]))
        return [NonFungibleTransferTransaction(
            sender=AbiDecoder.bytes32_to_address(event["topics"][1]),
            recipient=AbiDecoder.bytes32_to_address(event["topics"][2]),
            tx_hash=HexStr(event["transactionHash"].hex()),
            token_id=token_id)]

    @staticmethod
    def from_event_entry(event_entry: AttributeDict) -> List["TransferTransaction"]:
        return [NonFungibleTransferTransaction(
            sender=event_entry["args"]["from"],
            recipient=event_entry["args"]["to"],
            tx_hash=event_entry["transactionHash"].hex(),
            token_id=event_entry["args"]["tokenId"])]

    def __str__(self):
        return f"Token {self.token_id} sent {self.sender} -> {self.recipient}"


@dataclasses.dataclass
class ERC1155TransferTransaction(FungibleTransferTransaction, NonFungibleTransferTransaction):
    operator: ChecksumAddress

    event_hash_single = Web3.keccak(text="TransferSingle(address,address,address,uint256,uint256)")
    event_hash_batch = Web3.keccak(text="TransferBatch(address,address,address,uint256[],uint256[])")

    event_name_single = "TransferSingle"
    event_name_batch = "TransferBatch"

    def to_token_transfer_model(self) -> TokenTransfer:
        model_instance = TokenTransfer()
        model_instance.operator = self.operator
        model_instance.amount = self.amount
        model_instance.sender = self.sender
        model_instance.recipient = self.recipient
        model_instance.token_id = self.token_id
        model_instance.tx_hash = self.tx_hash
        return model_instance

    @classmethod
    def from_raw_log(cls, event: LogReceipt) -> List["TransferTransaction"]:
        if len(event["topics"]) < 4:
            return []
        data = HexBytes(event["data"])
        operator = AbiDecoder.bytes32_to_address(event["topics"][1])
        sender = AbiDecoder.bytes32_to_address(event["topics"][2])
        recipient = AbiDecoder.bytes32_to_address(event["topics"][3])
        if event["topics"][0] == cls.event_hash_single:
            return cls._parse_single_transfer(event, data, operator, sender, recipient)
        elif event["topics"][0] == cls.event_hash_batch:
            return cls._parse_batch_transfer(event, data, operator, sender, recipient)
        else:
            return []

    def __str__(self):
        return f"Tokens {self.amount} of ID {self.token_id} sent {self.sender} -> {self.recipient}"

    @classmethod
    def from_event_entry(cls, event_entry: AttributeDict) -> List["TransferTransaction"]:
        result: List[TransferTransaction] = []
        if event_entry["event"] == cls.event_name_batch:
            ids: List[int] = list(map(int, event_entry["args"]["ids"]))
            values: List[int] = list(map(int, event_entry["args"]["values"]))
            if len(ids) != len(values):
                return []
            for (i, token_id) in enumerate(ids):
                value = values[i]
                result.append(
                    ERC1155TransferTransaction(
                        operator=event_entry["args"]["operator"],
                        sender=event_entry["args"]["from"],
                        recipient=event_entry["args"]["to"],
                        tx_hash=event_entry["transactionHash"].hex(),
                        token_id=token_id,
                        amount=value))
        elif event_entry["event"] == cls.event_name_single:
            result.append(ERC1155TransferTransaction(
                operator=event_entry["args"]["operator"],
                sender=event_entry["args"]["from"],
                recipient=event_entry["args"]["to"],
                tx_hash=event_entry["transactionHash"].hex(),
                token_id=event_entry["args"]["id"],
                amount=event_entry["args"]["value"]))
        return result

    @classmethod
    def _parse_token_info_from_data(cls, data: HexBytes) -> Tuple[int, int]:
        return AbiDecoder.bytes32_to_uint256(data[:32]), AbiDecoder.bytes32_to_uint256(data[32:])

    @classmethod
    def _parse_token_info_from_topics(cls, topics: Sequence[HexBytes]) -> Tuple[int, int]:
        return AbiDecoder.bytes32_to_uint256(topics[4]), AbiDecoder.bytes32_to_uint256(topics[5])

    @classmethod
    def _parse_single_transfer(cls,
                               event: LogReceipt,
                               data: HexBytes,
                               operator: ChecksumAddress,
                               sender: ChecksumAddress,
                               recipient: ChecksumAddress) -> List["TransferTransaction"]:
        if len(event["topics"]) == 6:
            token_id, amount = cls._parse_token_info_from_topics(event["topics"])
        else:
            if len(data) < 64:
                return []
            token_id, amount = cls._parse_token_info_from_data(data)
        return [ERC1155TransferTransaction(
            operator=operator,
            sender=sender,
            recipient=recipient,
            tx_hash=HexStr(event["transactionHash"].hex()),
            token_id=token_id,
            amount=amount)]

    @classmethod
    def _parse_batch_transfer(cls,
                              event: LogReceipt,
                              data: HexBytes,
                              operator: ChecksumAddress,
                              sender: ChecksumAddress,
                              recipient: ChecksumAddress):
        result: List[TransferTransaction] = []
        ids_location = AbiDecoder.bytes32_to_uint256(data[:32])
        amounts_location = AbiDecoder.bytes32_to_uint256(data[32:64])
        ids = AbiDecoder.bytes_to_int_array(data, ids_location)
        amounts = AbiDecoder.bytes_to_int_array(data, amounts_location)
        if len(ids) != len(amounts):
            logger.warning(f"Bad event on transaction {event['transactionHash'].hex()}")
            return result
        for (i, token_id) in enumerate(ids):
            amount = amounts[i]
            result.append(ERC1155TransferTransaction(
                operator=operator,
                sender=sender,
                recipient=recipient,
                token_id=token_id,
                amount=amount,
                tx_hash=HexStr(event["transactionHash"].hex())))
        return result
