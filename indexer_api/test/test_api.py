from django.test import TestCase

from indexer_api.models import Network, Indexer, IndexerStrategy, IndexerType, Token, TokenType, TokenStrategy, \
    TokenBalance, TokenTransfer


class NetworkAPITestCase(TestCase):
    chain_ids = [42, 56, 80001]

    def setUp(self) -> None:
        for i, chain_id in enumerate(self.chain_ids):
            Network.objects.create(chain_id=chain_id, name=f"Network #{i + 1}",
                                   rpc_url=f"http://dummy-rpc-of-chain-{chain_id}:8000")

    def test_should_give_list_of_networks(self):
        response = self.client.get("/indexer_api/networks/").json()
        actual_ids = list(map(lambda network: network["chain_id"], response["results"]))
        self.assertEqual(actual_ids, self.chain_ids)

    def test_should_give_details_by_chain_id(self):
        details = self.client.get(f"/indexer_api/networks/{self.chain_ids[0]}/").json()
        self.assertEqual(details["name"], "Network #1")


class IndexerAPITestCase(TestCase):
    indexers = ["bsc-busd-tracker", "polygon-usdt-tracker"]

    def setUp(self) -> None:
        Indexer.objects.create(name=self.indexers[0], last_block=0, network=Network.objects.create(
            chain_id=56, name=f"Binance Mainnet", rpc_url=f"http://rpc-bnb"), strategy=IndexerStrategy.token_scan,
                               type=IndexerType.transfer_indexer)
        Indexer.objects.create(name=self.indexers[1], last_block=0, network=Network.objects.create(
            chain_id=137, name=f"Polygon Mainnet", rpc_url=f"http://rpc-poly"), strategy=IndexerStrategy.token_scan,
                               type=IndexerType.transfer_indexer)

    def test_should_give_list_of_indexers(self):
        response = self.client.get("/indexer_api/indexers/").json()
        actual_indexers_names = list(map(lambda indexer: indexer["name"], response["results"]))
        self.assertEqual(self.indexers, actual_indexers_names)

    def test_should_give_details_on_indexer_by_name(self):
        response = self.client.get(f"/indexer_api/indexers/{self.indexers[0]}/").json()
        self.assertEqual(response["network"]["chain_id"], 56)


class TokenAPITestCase(TestCase):
    network_1: Network
    network_2: Network

    token_address_1 = "0x22E837C1E3380e8f38758C8490d9865433bF3ad5"
    token_address_2 = "0xFDF855fFbC0f44d0Ba2b75170b6Dee18aa379e86"

    def setUp(self) -> None:
        self.network_1 = Network.objects.create(
            chain_id=56, name=f"Binance Mainnet", rpc_url=f"http://rpc-bnb")
        self.network_2 = Network.objects.create(
            chain_id=137, name=f"Polygon Mainnet", rpc_url=f"http://rpc-poly")
        Token.objects.create(address=self.token_address_1, name="Binance USDT", network=self.network_1,
                             type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)
        Token.objects.create(address=self.token_address_1, name="Polygon USDT", network=self.network_2,
                             type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)
        Token.objects.create(address=self.token_address_2, name="Binance USDC", network=self.network_1,
                             type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)
        Token.objects.create(address=self.token_address_2, name="Polygon USDC", network=self.network_2,
                             type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)

    def test_should_give_list_of_tokens(self):
        response = self.client.get("/indexer_api/tokens/").json()
        self.assertEqual(4, len(response["results"]))

    def test_should_give_tokens_by_address(self):
        response = self.client.get(f"/indexer_api/tokens/?search={self.token_address_1}").json()
        self.assertEqual(2, len(response["results"]))
        self.assertEqual(response["results"][0]["name"], "Binance USDT")
        self.assertEqual(response["results"][1]["name"], "Polygon USDT")

    def test_should_give_tokens_by_network(self):
        response = self.client.get(f"/indexer_api/tokens/?search=137").json()
        self.assertEqual(2, len(response["results"]))
        self.assertEqual("Polygon USDT", response["results"][0]["name"])
        self.assertEqual("Polygon USDC", response["results"][1]["name"])


class BalanceAPITestCase(TestCase):
    binance: Network
    polygon: Network

    holder: str

    erc20: Token
    erc721enumerable: Token
    native: Token
    erc721: Token
    erc1155: Token

    def setUp(self) -> None:
        self.holder = "0xC7Ff9Ab002128232415A76B2fcf43029B3Ed9c92"
        self.binance = Network.objects.create(chain_id=56, name=f"Binance Mainnet", rpc_url=f"http://rpc-bnb")
        self.polygon = Network.objects.create(chain_id=137, name=f"Polygon Mainnet", rpc_url=f"http://rpc-poly")
        self.erc20 = Token.objects.create(address="0x1F98F33A06FB167f5c1856bddEeEBB030C474A68", name="Binance BUSD",
                                          network=self.binance,
                                          type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)
        self.erc721enumerable = Token.objects.create(address="0xF7a2C91237C7044ECf7d65D519A76E45Ba79fEF6",
                                                     name="Binance NFT", network=self.binance,
                                                     type=TokenType.erc721enumerable,
                                                     strategy=TokenStrategy.event_based_transfer)
        self.native = Token.objects.create(address=None, name="Binance BNB", network=self.binance,
                                           type=TokenType.native, strategy=TokenStrategy.receipt_based_transfer)
        self.erc721 = Token.objects.create(address="0x8e242Aebf76eE4F29e247cA7DE8a89542eed9eb4", name="Polygon NFT",
                                           network=self.polygon,
                                           type=TokenType.erc721, strategy=TokenStrategy.event_based_transfer)
        self.erc1155 = Token.objects.create(address="0x51ffE6985e7B8FB4c8A356DABa5BD5c489a9B489",
                                            name="Polygon ERC1155",
                                            network=self.polygon,
                                            type=TokenType.erc1155, strategy=TokenStrategy.event_based_transfer)

        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc20, amount=100)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc721enumerable, token_id=1)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc721enumerable, token_id=2)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc721enumerable, token_id=3)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc721, amount=3)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.erc1155, token_id=101, amount=99)
        TokenBalance.objects.create(holder=self.holder, token_instance=self.native, amount=2 ** 256 - 1)

    def test_should_give_balances_on_all_defined_tokens_properly(self):
        response = self.client.get(f"/indexer_api/balances/holder/{self.holder}/").json()
        binance_tokens = response["56"]
        self.assertEqual(3, len(binance_tokens.keys()))
        self.assertEqual(binance_tokens[self.erc20.address]["balance"], "100")
        self.assertEqual(binance_tokens[self.erc721enumerable.address]["balance"], ["1", "2", "3"])
        self.assertEqual(binance_tokens["null"]["balance"],
                         str(2 ** 256 - 1))  # null is a string literal for native token address
        polygon_tokens = response["137"]
        self.assertEqual(2, len(polygon_tokens.keys()))
        self.assertEqual(polygon_tokens[self.erc721.address]["balance"], "3")

        self.assertEqual(polygon_tokens[self.erc1155.address]["balance"], {"101": "99"})


class TransferAPITestCase(TestCase):
    binance: Network
    alice: str
    bob: str
    eva: str

    def setUp(self) -> None:
        self.binance = Network.objects.create(chain_id=56, name=f"Binance Mainnet", rpc_url=f"http://rpc-bnb")
        self.alice = "0x6197978A04d972FB3423b756b13Dd9c77F868181"
        self.bob = "0x80B68136475c68ec9346Fe45Aa7d538EA4282bbB"
        self.eva = "0xEdE8dE76d06858913cfFB84e1563bB6571e4ff3E"
        self.erc20 = Token.objects.create(address="0xB2960e178a899B218B56308Bb3D4858f40A33Ff6", name="USDC",
                                          network=self.binance,
                                          type=TokenType.erc20, strategy=TokenStrategy.event_based_transfer)
        self.erc721enumerable = Token.objects.create(address="0x70805Da703Fb5d1224b20bd1693E24179286ACd4",
                                                     name="NFT enumerable", network=self.binance,
                                                     type=TokenType.erc721enumerable,
                                                     strategy=TokenStrategy.event_based_transfer)
        self.native = Token.objects.create(address=None, name="BNB", network=self.binance,
                                           type=TokenType.native, strategy=TokenStrategy.receipt_based_transfer)
        self.erc721 = Token.objects.create(address="0x9183FB838656Be423345Bb1Ff9a941AD27b84FC3", name="NFT",
                                           network=self.binance,
                                           type=TokenType.erc721, strategy=TokenStrategy.event_based_transfer)
        self.erc1155 = Token.objects.create(address="0xB8c50A9799a797485C14490442A1442aC3853b8B",
                                            name="ERC1155",
                                            network=self.binance,
                                            type=TokenType.erc1155, strategy=TokenStrategy.event_based_transfer)
        self.some_tx_hash = "0x96b7c841052bfa53bd72b0247f40538a19f7d374557f9e5bee53951bd9b3cb4a"
        TokenTransfer.objects.create(sender=self.alice, recipient=self.bob,
                                     tx_hash=self.some_tx_hash,
                                     token_instance=self.erc20, amount=100
                                     )
        TokenTransfer.objects.create(sender=self.bob, recipient=self.alice,
                                     tx_hash="0x91d63df2297a7575827bb18f15802ae32986eb640327646ae883844dad417a4b",
                                     token_instance=self.erc20, amount=100
                                     )
        TokenTransfer.objects.create(sender=self.alice, recipient=self.bob,
                                     tx_hash="0xf371502682b7c5c5cab1c326ce487a97ff20ad913b308215fe9a57c88dc8ae54",
                                     token_instance=self.erc20, amount=1100
                                     )
        TokenTransfer.objects.create(sender=self.alice, recipient=self.eva,
                                     tx_hash="0xf57cfe2a1289ca891af21108b87a435c7df9ec9bed73656d8081fd2d1e391c62",
                                     token_instance=self.native, amount=100
                                     )
        TokenTransfer.objects.create(sender=self.bob, recipient=self.eva,
                                     tx_hash="0xaaf69cf137bd1a0dd51805139c31139dff8ff08f01267ed53dc8bc8d0fd212de",
                                     token_instance=self.erc721, token_id=1
                                     )
        TokenTransfer.objects.create(sender=self.bob, recipient=self.alice,
                                     tx_hash="0x93fca39c03a786ada61e6bfd2d344a6d66ec6a6484964abd0cebab8faaa80e3a",
                                     token_instance=self.erc721enumerable, token_id=1
                                     )
        TokenTransfer.objects.create(sender=self.bob, recipient=self.alice,
                                     tx_hash="0x52518b6f7ea1e3af222c8cc9becc83981c4db708ffc21267f54a89cad3cc34db",
                                     token_instance=self.erc1155, token_id=1, amount=100
                                     )

    def test_should_give_list_of_transfers(self):
        response = self.client.get("/indexer_api/transfers/").json()
        self.assertEqual(7, len(response["results"]))

    def test_should_give_transfer_details(self):
        response = self.client.get(f"/indexer_api/transfers/{self.some_tx_hash}/").json()
        self.assertEqual(self.alice, response["sender"])
        self.assertEqual(self.bob, response["recipient"])
        self.assertEqual("100", response["token_transferred"]["amount"])
        self.assertEqual("erc20", response["token_transferred"]["type"])
        self.assertEqual(self.erc20.address, response["token_transferred"]["token"])

    def test_should_give_transfers_by_participant(self):
        response = self.client.get(f"/indexer_api/transfers/?search={self.eva}").json()
        self.assertEqual(2, len(response["results"]))

    def test_should_give_transfers_by_token(self):
        response = self.client.get(f"/indexer_api/transfers/?search={self.erc20.address}").json()
        self.assertEqual(3, len(response["results"]))
