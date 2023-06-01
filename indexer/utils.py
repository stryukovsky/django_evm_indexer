from typing import List, Literal
from web3.types import HexBytes, ChecksumAddress
from web3 import Web3


class AbiDecoder:
    slot_size = 32
    byteorder: Literal["big", "little"] = "big"

    @classmethod
    def bytes32_to_int(cls, value: bytes) -> int:
        return int.from_bytes(value, byteorder=cls.byteorder)

    @classmethod
    def bytes_to_int_array(cls, data: bytes, array_location: int) -> List[int]:
        values = []
        length = cls.bytes32_to_int(data[array_location: array_location + cls.slot_size])
        start = array_location + cls.slot_size
        for i in range(length):
            values.append(cls.bytes32_to_int(data[start + i * cls.slot_size: start + (i + 1) * cls.slot_size]))
        return values

    @classmethod
    def bytes32_to_address(cls, value: HexBytes) -> ChecksumAddress:
        return Web3.to_checksum_address(value.hex()[26:])

    @classmethod
    def bytes32_to_uint256(cls, value: HexBytes) -> int:
        return int.from_bytes(value, byteorder="big")
