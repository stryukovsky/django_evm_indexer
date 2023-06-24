from typing import List

from indexer.transfer_fetchers import EventTransferFetcher
from indexer.transfer_transactions import TransferTransaction
from indexer.transfer_transactions import FungibleTransferTransaction
from web3 import Web3
from web3.types import HexStr


class EventTransferFetcherMock(EventTransferFetcher):
    # this transaction should be returned if eth_filter function is the choice
    mock_transfer_fetched_by_standard_filter = FungibleTransferTransaction(
        Web3.to_checksum_address("0x3f81B722F0C63Ec48991FADB2C361c0E61b3492A"),
        Web3.to_checksum_address("0x0dA5ad5Bc54b955c9156B8c3f86AaC7F5E65908C"),
        HexStr("0x4dc77d261089c354ef325fe15945fe349a9beae7acf6b17ee16a0e32eec7b39e"),
        10000
    )

    mock_transfer_fetched_by_raw_filter = FungibleTransferTransaction(
        Web3.to_checksum_address("0x64EE10d587051c1114a058F30eD26cBB5AbB914A"),
        Web3.to_checksum_address("0x6608E122609648107B6Afd0480B3D2ea0818d3df"),
        HexStr("0x3f55f4F3d96fA3BCFEe94D5526ddb8abC447cbE59a9beae7acf6b17ee16a0e32"),
        500
    )

    def _get_events_with_standard_filter(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        return [
            self.mock_transfer_fetched_by_standard_filter
        ]

    def _get_events_with_raw_filter(self, from_block: int, to_block: int) -> List[TransferTransaction]:
        return [
            self.mock_transfer_fetched_by_raw_filter
        ]

    def _mock__set_network_type(self, network_type: str):
        self.network_type = network_type
