from django.test import TestCase
from indexer_api.models import Network, Token, TokenBalance, TokenTransfer, Indexer
from indexer_api.models import NetworkType, TokenStrategy
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError


class NetworkTestCase(TestCase):
    network: Network
    chain_id: int

    def setUp(self) -> None:
        self.chain_id = 1
        self.network = Network.objects.create(chain_id=self.chain_id, name="Test network", rpc_url="url://simple",
                                              max_step=1000,
                                              type=NetworkType.filterable, need_poa=True)

    def test_cannot_create_two_networks_with_same_chain_id(self):
        try:
            Network.objects.create(chain_id=self.chain_id, name="Test network", rpc_url="url://second_url_in_pool",
                                   max_step=1000, type=NetworkType.filterable, need_poa=True)
        except Exception:
            self.assertTrue(True)

    def test_network_can_have_valid_url_as_rpc_url(self):
        valid_url = "https://rpc.testnet.network"
        Network(chain_id=123123, name="Test network", rpc_url=valid_url,
                max_step=1000, type=NetworkType.filterable, need_poa=True).save()

    def test_network_cannot_have_negative_step(self):
        negative_step = -1000
        self.assertRaises(IntegrityError, lambda: Network(chain_id=self.chain_id, name="Test network",
                                                          rpc_url="https://rpc.testnet.network",
                                                          max_step=negative_step, type=NetworkType.filterable,
                                                          need_poa=True).save())


class TokenTestCase(TestCase):
    first_token_address: str
    second_token_address: str

    first_network_chain_id: int
    second_network_chain_id: int

    first_network: Network
    second_network: Network

    def setUp(self) -> None:
        self.first_token_address = "0x63CE09b8654390415BE84155eC5268cB4e206b63"
        self.second_token_address = "0xdEeAe2a40467970142fa0FF3EF79e283Cf60a021"
        self.first_network_chain_id = 54
        self.second_network_chain_id = 137
        self.first_network = Network.objects.create(chain_id=self.first_network_chain_id, name="Binance",
                                                    rpc_url="https://rpc.binance.network",
                                                    max_step=1000, type=NetworkType.filterable,
                                                    need_poa=True)
        self.second_network = Network.objects.create(chain_id=self.second_network_chain_id, name="Polygon",
                                                     rpc_url="https://rpc.polygon.network",
                                                     max_step=1000, type=NetworkType.names,
                                                     need_poa=True)

    def test_tokens_cannot_have_same_address_inside_one_chain(self):
        Token.objects.create(address=self.first_token_address, name="USDT",
                             strategy=TokenStrategy.event_based_transfer,
                             network=self.first_network)
        self.assertRaises(Exception,
                          lambda: Token.objects.create(address=self.first_token_address, name="Some other token",
                                                       strategy=TokenStrategy.event_based_transfer,
                                                       network=self.first_network))

    def test_tokens_can_have_same_address_on_separate_chains(self):
        Token.objects.create(address=self.first_token_address, name="USDT",
                             strategy=TokenStrategy.event_based_transfer,
                             network=self.first_network)
        Token.objects.create(address=self.first_token_address, name="USDT",
                             strategy=TokenStrategy.event_based_transfer,
                             network=self.second_network)
        count = Token.objects.filter(address=self.first_token_address).count()
        self.assertEqual(count, 2)

    def test_tokens_can_have_same_name(self):
        Token.objects.create(address=self.first_token_address, name="Some Token",
                             strategy=TokenStrategy.event_based_transfer,
                             network=self.second_network)
        Token.objects.create(address=self.second_token_address, name="Some Token",
                             strategy=TokenStrategy.event_based_transfer,
                             network=self.second_network)
        count = Token.objects.filter(name="Some Token").count()
        self.assertEqual(count, 2)
