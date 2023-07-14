import json

from django.test import TestCase
from indexer.balance_fetchers import AbstractBalanceFetcher, SimpleBalanceFetcher
from indexer.balance_callers import ERC20BalanceCaller, ERC721BalanceCaller, ERC721EnumerableBalanceCaller, \
    NativeBalanceFetcher
from indexer_api.models import TokenType, Token, Network, NetworkType, TokenStrategy, Indexer, IndexerStrategy, \
    IndexerStatus, IndexerType
from web3.auto import w3


class BalanceFetcherABIDispatchTestCase(TestCase):
    def test_should_give_erc20_abi(self):
        actual_abi = AbstractBalanceFetcher._get_abi(TokenType.erc20)
        with open("indexer/abi/ERC20.json") as file:
            expected_abi = json.load(file)
        self.assertEqual(actual_abi, expected_abi)

    def test_should_give_erc721_abi(self):
        actual_abi = AbstractBalanceFetcher._get_abi(TokenType.erc721)
        with open("indexer/abi/ERC721.json") as file:
            expected_abi = json.load(file)
        self.assertEqual(actual_abi, expected_abi)

    def test_should_give_erc721enumerable_abi(self):
        actual_abi = AbstractBalanceFetcher._get_abi(TokenType.erc721enumerable)
        with open("indexer/abi/ERC721Enumerable.json") as file:
            expected_abi = json.load(file)
        self.assertEqual(actual_abi, expected_abi)

    def test_should_give_erc1155_abi(self):
        actual_abi = AbstractBalanceFetcher._get_abi(TokenType.erc1155)
        with open("indexer/abi/ERC1155.json") as file:
            expected_abi = json.load(file)
        self.assertEqual(actual_abi, expected_abi)


class BalanceFetcherCallerDispatchTestCase(TestCase):
    network: Network
    indexer: Indexer
    holder: str

    def setUp(self) -> None:
        self.holder = "0xe4630F2Ea04466103138cA8C6EC1F448ced6fA93"
        self.network = Network.objects.create(chain_id=1, name="Ethereum", rpc_url="localhost:8000", max_step=1000,
                                              type=NetworkType.no_filters, need_poa=True,
                                              explorer_url="https://example.com")
        self.indexer = Indexer.objects.create(name="test-indexer", last_block=123, network=self.network,
                                              strategy=IndexerStrategy.specified_holders,
                                              short_sleep_seconds=1,
                                              long_sleep_seconds=1, strategy_params={
                                                  "holders": [self.holder]
                                              }, status=IndexerStatus.on,
                                              type=IndexerType.balance_indexer)

    def test_should_give_erc20_caller(self):
        token = Token.objects.create(address="0x77FeF7746ba17FC58C8Fd6ceD26b5e248110CD69", name="DAI",
                                     strategy=TokenStrategy.event_based_transfer, network=self.network,
                                     type=TokenType.erc20)
        fetcher = SimpleBalanceFetcher(w3, token, self.indexer)
        caller = fetcher.balance_caller
        self.assertEqual(type(caller), ERC20BalanceCaller)

    def test_should_give_erc721_caller(self):
        token = Token.objects.create(address="0x77FeF7746ba17FC58C8Fd6ceD26b5e248110CD69", name="NFT",
                                     strategy=TokenStrategy.event_based_transfer, network=self.network,
                                     type=TokenType.erc721)
        fetcher = SimpleBalanceFetcher(w3, token, self.indexer)
        caller = fetcher.balance_caller
        self.assertEqual(type(caller), ERC721BalanceCaller)

    def test_should_give_erc721enumerable_caller(self):
        token = Token.objects.create(address="0x77FeF7746ba17FC58C8Fd6ceD26b5e248110CD69", name="NFT",
                                     strategy=TokenStrategy.event_based_transfer, network=self.network,
                                     type=TokenType.erc721enumerable)
        fetcher = SimpleBalanceFetcher(w3, token, self.indexer)
        caller = fetcher.balance_caller
        self.assertEqual(type(caller), ERC721EnumerableBalanceCaller)

    def test_should_give_native_caller(self):
        token = Token.objects.create(address=None, name="DAI",
                                     strategy=TokenStrategy.receipt_based_transfer, network=self.network,
                                     type=TokenType.native)
        fetcher = SimpleBalanceFetcher(w3, token, self.indexer)
        caller = fetcher.balance_caller
        self.assertEqual(type(caller), NativeBalanceFetcher)
