import json
from typing import cast

from django.test import TestCase

from indexer.transfer_fetchers import EventTransferFetcher, ReceiptTransferFetcher
from indexer.transfer_transactions import FungibleTransferTransaction, NonFungibleTransferTransaction, \
    ERC1155TransferTransaction, NativeCurrencyTransferTransaction
from indexer_api.models import Token, Network, NetworkType, TokenStrategy, TokenType
from web3.auto import w3

from indexer_api.test.mock.transfer_fetchers_mock import EventTransferFetcherMock
from unittest.mock import Mock
from web3 import Web3
from web3.types import BlockData, HexBytes, TxReceipt
from web3.datastructures import AttributeDict


# noinspection DuplicatedCode
class EventTransferFetcherTestCase(TestCase):
    network_with_eth_filter: Network
    network_without_filtering: Network
    token_with_eth_filter: Token
    token_without_filtering: Token

    def setUp(self) -> None:
        self.network_with_eth_filter = Network.objects.create(chain_id=1,
                                                              name="Ethereum mainnet",
                                                              rpc_url="https://ethereum.org",
                                                              max_step=1000,
                                                              type=NetworkType.filterable,
                                                              need_poa=True)
        self.network_without_filtering = Network.objects.create(chain_id=137,
                                                                name="Polygon mainnet",
                                                                rpc_url="https://polygon.org",
                                                                max_step=1000,
                                                                type=NetworkType.no_filters,
                                                                need_poa=True)
        self.token_with_eth_filter = Token.objects.create(address="0xeB3D38AF7f3594014cf23C273f21EEd623e1E0a3",
                                                          name="DAI",
                                                          network=self.network_with_eth_filter,
                                                          strategy=TokenStrategy.event_based_transfer,
                                                          type=TokenType.erc20)
        self.token_without_filtering = Token.objects.create(address="0xc1cE8d27682D3256Cd035cBE4147ED0760981CBD",
                                                            name="USDT",
                                                            network=self.network_without_filtering,
                                                            strategy=TokenStrategy.event_based_transfer,
                                                            type=TokenType.erc20)

    def test_should_fail_if_token_type_is_bad(self):
        self.assertRaises(ValueError,
                          lambda: EventTransferFetcher._get_abi("some_token_type_which_totally_is_impossible"))

    def test_should_give_erc20_abi_for_token_type(self):
        abi = EventTransferFetcher._get_abi(TokenType.erc20)
        with open("indexer/abi/ERC20.json", "r") as file:
            expected = json.load(file)
            self.assertEqual(abi, expected)

    def test_should_give_erc721_abi_for_nft_token_type(self):
        abi = EventTransferFetcher._get_abi(TokenType.erc721)
        with open("indexer/abi/ERC721.json", "r") as file:
            expected = json.load(file)
            self.assertEqual(abi, expected)

    def test_should_give_erc721_abi_for_enumerable_token_type(self):
        abi = EventTransferFetcher._get_abi(TokenType.erc721enumerable)
        with open("indexer/abi/ERC721.json", "r") as file:
            expected = json.load(file)
            self.assertEqual(abi, expected)

    def test_should_give_erc1155_abi_for_token_type(self):
        abi = EventTransferFetcher._get_abi(TokenType.erc1155)
        with open("indexer/abi/ERC1155.json", "r") as file:
            expected = json.load(file)
            self.assertEqual(abi, expected)

    def test_should_fail_give_events_if_token_type_is_bad(self):
        self.assertRaises(ValueError,
                          lambda: EventTransferFetcher._get_event_names(TokenType.native))
        self.assertRaises(ValueError,
                          lambda: EventTransferFetcher._get_event_names("some_token_type_which_is_impossible"))

    def test_should_give_events_erc20(self):
        events = EventTransferFetcher._get_event_names(TokenType.erc20)
        self.assertEqual(events, ["Transfer"])

    def test_should_give_events_erc721(self):
        events = EventTransferFetcher._get_event_names(TokenType.erc721)
        self.assertEqual(events, ["Transfer"])

    def test_should_give_events_erc721enumerable(self):
        events = EventTransferFetcher._get_event_names(TokenType.erc721enumerable)
        self.assertEqual(events, ["Transfer"])

    def test_should_give_events_erc1155(self):
        events = EventTransferFetcher._get_event_names(TokenType.erc1155)
        self.assertEqual(events, ["TransferSingle", "TransferBatch"])

    def test_should_fail_give_transfer_transaction_type_for_bad_token_type(self):
        self.assertRaises(ValueError,
                          lambda: EventTransferFetcher._get_transfer_transaction_type("some_bad_token_type"))

    def test_should_give_transfer_transaction_type_for_erc20(self):
        transfer_transaction_type = EventTransferFetcher._get_transfer_transaction_type(TokenType.erc20)
        self.assertEqual(FungibleTransferTransaction, transfer_transaction_type)

    def test_should_give_transfer_transaction_type_for_erc721(self):
        transfer_transaction_type = EventTransferFetcher._get_transfer_transaction_type(TokenType.erc721)
        self.assertEqual(NonFungibleTransferTransaction, transfer_transaction_type)

    def test_should_give_transfer_transaction_type_for_erc721enumerable(self):
        transfer_transaction_type = EventTransferFetcher._get_transfer_transaction_type(TokenType.erc721enumerable)
        self.assertEqual(NonFungibleTransferTransaction, transfer_transaction_type)

    def test_should_give_transfer_transaction_type_for_erc1155(self):
        transfer_transaction_type = EventTransferFetcher._get_transfer_transaction_type(TokenType.erc1155)
        self.assertEqual(ERC1155TransferTransaction, transfer_transaction_type)

    def test_should_properly_dispatch_event_function_when_eth_filter_available(self):
        mocked_event_transfer_fetcher = EventTransferFetcherMock(w3, self.token_with_eth_filter)
        transfers = mocked_event_transfer_fetcher.get_transfers(100, 200)
        self.assertEqual(1, len(transfers))
        transfer = cast(FungibleTransferTransaction, transfers[0])
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_standard_filter.sender, transfer.sender)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_standard_filter.recipient,
                         transfer.recipient)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_standard_filter.tx_hash,
                         transfer.tx_hash)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_standard_filter.amount, transfer.amount)

    def test_should_properly_dispatch_event_function_when_only_raw_filters_available(self):
        mocked_event_transfer_fetcher = EventTransferFetcherMock(w3, self.token_without_filtering)
        transfers = mocked_event_transfer_fetcher.get_transfers(100, 200)
        self.assertEqual(1, len(transfers))
        transfer = cast(FungibleTransferTransaction, transfers[0])
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_raw_filter.sender, transfer.sender)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_raw_filter.recipient,
                         transfer.recipient)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_raw_filter.tx_hash,
                         transfer.tx_hash)
        self.assertEqual(mocked_event_transfer_fetcher.mock_transfer_fetched_by_raw_filter.amount, transfer.amount)

    def test_should_fail_when_mocked_bad_network_type(self):
        mocked_event_transfer_fetcher = EventTransferFetcherMock(w3, self.token_without_filtering)
        mocked_event_transfer_fetcher._mock__set_network_type("some_dummy_type_which_will_never_exist")
        self.assertRaises(NotImplementedError, lambda: mocked_event_transfer_fetcher.get_transfers(100, 200))


class ReceiptTransferFetcherTestCase(TestCase):
    sender: str
    recipient: str
    native_amount: int
    status: int

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Ethereum mainnet",
                                              rpc_url="https://ethereum.org",
                                              max_step=1000,
                                              type=NetworkType.filterable,
                                              need_poa=True)
        self.token = Token.objects.create(address=None,
                                          name="ETH",
                                          network=self.network,
                                          strategy=TokenStrategy.receipt_based_transfer,
                                          type=TokenType.native)
        self.w3 = cast(Web3, Mock())
        self.sender = "0xB29b5336b4aFe2B43ea989479B170cdd55EC8C6e"
        self.recipient = "0x1dDbFba689387f078449ff625454c5b302f6E9A4"
        self.native_amount = 1000000000

        # one of this txes has from, to and value fields defined as variables above
        # this tx must create a TokenTransfer model instance
        # eth_getBlock method here is mocked
        self.w3.eth.get_block = lambda _1, full_transactions: cast(BlockData, AttributeDict(  # type: ignore
            {
                'difficulty': 2,
                'proofOfAuthorityData': HexBytes('0xd883010101846765746888676f312e31362e33856c696e757800daf201'),
                'gasLimit': 85000000, 'gasUsed': 36243957,
                'hash': HexBytes('0xd08dca8c7d87780ca6f2faed2e12508d431939f7d7c3fa0d052f0744e1a47e55'),
                'logsBloom': HexBytes('0xcd3a3eff7ff3b4b53add7be5f79d24907a968de85e3ceed36e27e34ed177ec3df'),
                'miner': '0x8c4D90829CE8F72D0163c1D5Cf348a862d550630',
                'mixHash': HexBytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                'nonce': HexBytes('0x0000000000000000'),
                'number': 10000000,
                'parentHash': HexBytes('0x6b77d2519fc680931d57729aac79a1a30c9c7a9e684499d7ed52fa800f9c799c'),
                'receiptsRoot': HexBytes('0xb79d128fd3a477de5f13be54c22a68988f9ffa58673abf1dc923eb999e0188d7'),
                'sha3Uncles': HexBytes('0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347'),
                'size': 52112,
                'stateRoot': HexBytes('0xb530f1f7019001b0cd8ae1bb74bae78e199d15afa85b26dde55641e98b522a47'),
                'timestamp': 1628878142,
                'totalDifficulty': 19904614,
                'transactions': [
                    AttributeDict(
                        {'blockHash': HexBytes('0xd08dca8c7d87780ca6f2faed2e12508d431939f7d7c3fa0d052f0744e1a47e55'),
                         'blockNumber': 10000000,
                         'from': self.sender,
                         'gas': 180000,
                         'gasPrice': 1000000000000,
                         'hash': HexBytes('0x40d24ac73ae4214c97705477ef47f6c2d3059cf90f444fa87f64f6c1c141eddd'),
                         'input': '0x',
                         'nonce': 340,
                         'to': self.recipient,
                         'transactionIndex': 2,
                         'value': self.native_amount,
                         'type': 0,
                         'v': 148,
                         'r': HexBytes('0x74877a8b7c7606630aad90619f8e68ab66c0be44cbfa6f6cf111bd034c1bca96'),
                         's': HexBytes('0x74dce2f031fe1f434f74bf3cdc470a7a927fac8809031318cb69b5abe78cc667')}),
                ],
                'uncles': []})
                                                                   )
        self.status = 1
        self.w3.eth.get_transaction_receipt = lambda transaction_hash: cast(TxReceipt, AttributeDict({  # type: ignore
            'blockHash': HexBytes('0xd08dca8c7d87780ca6f2faed2e12508d431939f7d7c3fa0d052f0744e1a47e55'),
            'blockNumber': 10000000,
            'contractAddress': None,
            'cumulativeGasUsed': 120046,
            'effectiveGasPrice': 1500000000000,
            'from': self.sender,
            'gasUsed': 120046,
            'logs': [
                AttributeDict(
                    {
                        'address': self.recipient,
                        'topics': [],
                        'data': HexBytes('0x'),
                        'blockNumber': 10000000,
                        'transactionHash': HexBytes(
                            '0xec194fc84a8ccac78884ecdad4f9b8227d4ffb7f74f1b17b9539e5832df05572'),
                        'transactionIndex': 0,
                        'blockHash': HexBytes('0xd08dca8c7d87780ca6f2faed2e12508d431939f7d7c3fa0d052f0744e1a47e55'),
                        'logIndex': 0,
                        'removed': False})],
            'logsBloom': HexBytes('0x'),
            'status': self.status,
            'to': self.recipient,
            'transactionHash': HexBytes('0xec194fc84a8ccac78884ecdad4f9b8227d4ffb7f74f1b17b9539e5832df05572'),
            'transactionIndex': 0,
            'type': 0
        }
        ))

    def test_should_successfully_fetch_transaction(self):
        self.status = 1  # make the only tx in block have successful status
        native_currency_transfers = ReceiptTransferFetcher(self.w3, self.token).get_transfers(0, 0)
        self.assertEqual(1, len(native_currency_transfers))
        native_currency_transfer: NativeCurrencyTransferTransaction = cast(NativeCurrencyTransferTransaction,
                                                                           native_currency_transfers[0])
        self.assertEqual(self.sender, native_currency_transfer.sender)
        self.assertEqual(self.recipient, native_currency_transfer.recipient)
        self.assertEqual(self.native_amount, native_currency_transfer.amount)

    def test_should_skip_failed_tx(self):
        self.status = 0  # make the only tx in block failed
        native_currency_transfers = ReceiptTransferFetcher(self.w3, self.token).get_transfers(0, 0)
        self.assertEqual(0, len(native_currency_transfers))
