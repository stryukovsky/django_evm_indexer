from typing import List

from django.test import TestCase
from web3 import Web3
from web3.types import ChecksumAddress, HexStr

from indexer.strategies import SenderStrategy, RecipientStrategy, TokenScanStrategy
from indexer.transfer_transactions import FungibleTransferTransaction, ERC1155TransferTransaction, TransferTransaction
from indexer_api.models import Token, Network, NetworkType, TokenStrategy, TokenType, Indexer, IndexerStrategy, \
    IndexerStatus, IndexerType, TokenTransfer


class RecipientStrategyTestCase(TestCase):
    indexer: Indexer
    network: Network
    token: Token

    recipient: ChecksumAddress

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Ethereum mainnet",
                                              rpc_url="https://ethereum.org",
                                              max_step=1000,
                                              type=NetworkType.filterable,
                                              need_poa=True)
        self.recipient = Web3.to_checksum_address("0x2AFA0fC03097dDc0C25e32EbbcA71Da5E7a11938")
        self.token = Token.objects.create(address="0xeB3D38AF7f3594014cf23C273f21EEd623e1E0a3",
                                          name="DAI",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc20)
        self.indexer = Indexer.objects.create(name="test",
                                              last_block=1,
                                              network=self.network,
                                              strategy=IndexerStrategy.recipient,
                                              short_sleep_seconds=1,
                                              long_sleep_seconds=1,
                                              strategy_params={"recipient": self.recipient},
                                              status=IndexerStatus.on,
                                              type=IndexerType.transfer_indexer, )

    def test_should_filter_properly_transfers_and_save(self):
        RecipientStrategy(self.indexer).start(self.token, [
            FungibleTransferTransaction(
                sender=Web3.to_checksum_address("0xeeA573D4CDa98601D5cf3fC5AD0ef44258B1Bfa1"),
                recipient=self.recipient,
                tx_hash=HexStr("0xa235c8a71c1310d8b735c6dece3aa7215ecd6b80ba6d6a3dade0129b4147a089"),
                amount=1928349582294019934000000
            ),
            FungibleTransferTransaction(
                sender=Web3.to_checksum_address("0xe9910E99DFb4cD815C11c8558a34f0320D7bde43"),
                recipient=Web3.to_checksum_address("0x41Cc6CE1CEeb68c9c297e04F97aB786915B0Dc9f"),
                tx_hash=HexStr("0x85be5d6409db5c9b8976ab94480ce8053074a07acc63abc4079d0b6a1a493670"),
                amount=900
            ),
            FungibleTransferTransaction(
                sender=Web3.to_checksum_address("0x95c5A04406D3FB28DEfD0D3e63B554Ce3c2AFA07"),
                recipient=self.recipient,
                tx_hash=HexStr("0xeff41df5811f1c078cf3351020dba1aeacac1c6aa88d91bdb9b723e322592751"),
                amount=123
            ),
        ])

        transfers_with_recipient = TokenTransfer.objects.filter(recipient__iexact=self.recipient).count()
        # three transactions provided, only two of them has required recipient
        self.assertEqual(2, transfers_with_recipient)

    def test_should_properly_skip_already_indexed_tx(self):
        transaction = FungibleTransferTransaction(
            sender=Web3.to_checksum_address("0xeeA573D4CDa98601D5cf3fC5AD0ef44258B1Bfa1"),
            recipient=self.recipient,
            tx_hash=HexStr("0xa235c8a71c1310d8b735c6dece3aa7215ecd6b80ba6d6a3dade0129b4147a089"),
            amount=1928349582294019934000000
        )
        strategy = RecipientStrategy(self.indexer)
        strategy.start(self.token, [transaction])
        strategy.start(self.token, [transaction])

        transfers_with_recipient = TokenTransfer.objects.filter(recipient__iexact=self.recipient).count()
        # two same transfers should be skipped; only one is saved
        self.assertEqual(1, transfers_with_recipient)


class SenderStrategyTestCase(TestCase):
    indexer: Indexer
    network: Network
    token: Token

    sender: ChecksumAddress

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Polygon",
                                              rpc_url="https://polygonrpc.org",
                                              max_step=1000,
                                              type=NetworkType.no_filters,
                                              need_poa=True)
        self.sender = Web3.to_checksum_address("0x54fE6A81bc444F6efC75eb9b077cC8211Fe42Cc8")
        self.token = Token.objects.create(address="0xe5fC1d9fC7D881fF82BD87d1D60864A43691B3c3",
                                          name="USDT",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc20)
        self.indexer = Indexer.objects.create(name="test",
                                              last_block=1,
                                              network=self.network,
                                              strategy=IndexerStrategy.recipient,
                                              short_sleep_seconds=1,
                                              long_sleep_seconds=1,
                                              strategy_params={"sender": self.sender},
                                              status=IndexerStatus.on,
                                              type=IndexerType.transfer_indexer, )

    def test_should_filter_properly_transfers_and_save(self):
        SenderStrategy(self.indexer).start(self.token, [
            FungibleTransferTransaction(
                sender=self.sender,
                recipient=Web3.to_checksum_address("0x4265B8F48992ABfE30b0b59E7220005234eC7938"),
                tx_hash=HexStr("0x886da309f8bf657d7c51a525873a18b3ac27231b0c640b7e3a35a61c52e5a3e1"),
                amount=8100085800000000
            ),
            FungibleTransferTransaction(
                sender=Web3.to_checksum_address("0xBf9d31dc06F190901A7558bE6f18974699968bC7"),
                recipient=Web3.to_checksum_address("0x38Ab244f1365fb437c81072a8c0DCC854F675655"),
                tx_hash=HexStr("0x9d800e555197a9e21540e830789b33a00f28fe88c3b17299bea839ff04243268"),
                amount=1500000000000000
            ),
            FungibleTransferTransaction(
                sender=self.sender,
                recipient=Web3.to_checksum_address("0x26788C2164d42903eE7C214F39427d7220a48DCC"),
                tx_hash=HexStr("0x71cf97c73b9b3a1c85e87fe80f1267d6803d2d1bc7a6199fb753a437cb41e750"),
                amount=478300000000000000000
            ),
            FungibleTransferTransaction(
                sender=Web3.to_checksum_address("0x1840A553A900577915b7C2b09ADbAD290A62f937"),
                recipient=Web3.to_checksum_address("0xBc01145d64F40D54D525E5273afe8af69B7Bd0aC"),
                tx_hash=HexStr("0xb8495aaecb5350900054646c4b62e2814146de47593f0566ade86e772e36b646"),
                amount=514785000000000000000000
            ),
        ])

        transfers_with_sender = TokenTransfer.objects.filter(sender__iexact=self.sender).count()
        # three transactions provided, only two of them has required recipient
        self.assertEqual(2, transfers_with_sender)

    def test_should_properly_skip_already_indexed_tx(self):
        tx_hash = HexStr("0f7ea63a097a02af63b26703e3ea945495666a0deae39d9b34e0bf6c1f1d39df")
        recipient = Web3.to_checksum_address("0xf160bB78444d214ca49702aDCdcF8C9fB0Dd9558")
        amount = 512389000000000000
        transaction = FungibleTransferTransaction(
            sender=self.sender,
            recipient=recipient,
            tx_hash=tx_hash,
            amount=amount
        )
        strategy = SenderStrategy(self.indexer)
        strategy.start(self.token, [transaction])
        strategy.start(self.token, [transaction])

        transfers_with_recipient = TokenTransfer.objects.filter(sender__iexact=self.sender).count()
        # two same transfers should be skipped; only one is saved
        self.assertEqual(1, transfers_with_recipient)

        transfer: TokenTransfer = TokenTransfer.objects.get(tx_hash=tx_hash)
        self.assertEqual(self.sender, transfer.sender)
        self.assertEqual(recipient, transfer.recipient)
        self.assertEqual(amount, transfer.amount)


class ERC1155TransferHandleStrategyTestCase(TestCase):
    indexer: Indexer
    network: Network
    token: Token

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Polygon",
                                              rpc_url="https://polygonrpc.org",
                                              max_step=1000,
                                              type=NetworkType.no_filters,
                                              need_poa=True)
        self.token = Token.objects.create(address="0x69caab0600AA0eBC1B9f3688E58F8b18725b7d37",
                                          name="Some ERC1155",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc1155)
        self.indexer = Indexer.objects.create(name="test",
                                              last_block=1,
                                              network=self.network,
                                              strategy=IndexerStrategy.token_scan,
                                              short_sleep_seconds=1,
                                              long_sleep_seconds=1,
                                              strategy_params={},
                                              status=IndexerStatus.on,
                                              type=IndexerType.transfer_indexer)
        self.tx_hash = HexStr("0x767aa81e97c174cb8d69cf425e2bc97f6404a4c3a6c85f9f26b006c9e9aea6b5")
        self.sender = Web3.to_checksum_address("0xaf5d9a990d05b980b7393777b40568126ec6f585")
        self.recipient = Web3.to_checksum_address("0x432040fb721521f01753876b9893a9bf3ebdd83b")
        self.token_ids = [0xda0, 0xbeef, 0xcafe]
        self.amount = 5  # every token is minted with the same amount
        self.transactions: List[TransferTransaction] = []
        for token_id in self.token_ids:
            self.transactions.append(ERC1155TransferTransaction(
                operator=self.sender,
                sender=self.sender,
                recipient=self.recipient,
                tx_hash=self.tx_hash,
                token_id=token_id,
                amount=self.amount,
            ))

    def test_should_create_many_transfers_for_many_erc1155_transfers(self):
        TokenScanStrategy(self.indexer).start(self.token, self.transactions)

        count = TokenTransfer.objects.filter(tx_hash=self.tx_hash).count()
        self.assertEqual(3, count)
        for index, token_transfer in enumerate(TokenTransfer.objects.filter(tx_hash=self.tx_hash)):
            self.assertEqual(self.token_ids[index], token_transfer.token_id)

    def test_should_skip_already_indexed_erc1155_transfer(self):
        TokenScanStrategy(self.indexer).start(self.token, self.transactions)

        # we also try to add some transfer with already saved a pair of tx_hash and token_id
        TokenScanStrategy(self.indexer).start(self.token, [
            ERC1155TransferTransaction(
                operator=self.sender,
                sender=self.sender,
                recipient=self.recipient,
                tx_hash=self.tx_hash,
                token_id=self.token_ids[0],
                amount=self.amount,
            )
        ])
        count = TokenTransfer.objects.filter(tx_hash=self.tx_hash).count()
        self.assertEqual(3, count)
