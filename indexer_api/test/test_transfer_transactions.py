from typing import cast, List

from django.test import TestCase
from web3 import Web3
from web3.datastructures import AttributeDict
from web3.types import ChecksumAddress, HexStr, HexBytes, LogReceipt

from indexer.transfer_transactions import NativeCurrencyTransferTransaction, FungibleTransferTransaction, \
    NonFungibleTransferTransaction, ERC1155TransferTransaction
from indexer_api.models import TokenTransfer, Token, Network, NetworkType, TokenStrategy, TokenType


class NativeCurrencyTransferTransactionTestCase(TestCase):
    network: Network
    token: Token
    sender: ChecksumAddress
    recipient: ChecksumAddress
    amount: int
    tx_hash: HexStr

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
        self.sender = Web3.to_checksum_address("0xc0904D38b1D6050f31Bcd34d571DEbE07ce83E8a")
        self.recipient = Web3.to_checksum_address("0xb8bf47eD3F57fC8e431F51FBC821e3F9BEa588B4")
        self.tx_hash = HexStr("0x5328ad494b7ec64f6f239bb226b0968efc17b7b3564eced909a196bad9dcaca0")
        self.amount = 1000

    def test_should_create_model_instance_from_transfer(self):
        transfer = NativeCurrencyTransferTransaction(self.sender, self.recipient, self.tx_hash, self.amount)
        model_instance = transfer.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        model_instance_from_database = TokenTransfer.objects.get()
        self.assertEqual(model_instance_from_database.sender, self.sender)
        self.assertEqual(model_instance_from_database.recipient, self.recipient)
        self.assertEqual(model_instance_from_database.tx_hash, self.tx_hash)
        self.assertEqual(model_instance_from_database.token_instance, self.token)


# noinspection DuplicatedCode
class FungibleTransferTransactionTestCase(TestCase):
    network: Network
    token: Token
    sender: str
    raw_sender: str

    recipient: str
    raw_recipient: str

    amount: int
    raw_amount: str

    tx_hash: str
    event_entry: AttributeDict

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Ethereum mainnet",
                                              rpc_url="https://ethereum.org",
                                              max_step=1000,
                                              type=NetworkType.filterable,
                                              need_poa=True)
        self.token = Token.objects.create(address="0xeB3D38AF7f3594014cf23C273f21EEd623e1E0a3",
                                          name="DAI",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc20)
        self.sender = "0xdb6f2ed702823b903b6d185f68bdf715d1b3af76"
        self.raw_sender = "0x000000000000000000000000db6f2ed702823b903b6d185f68bdf715d1b3af76"

        self.recipient = "0x7ab6c736baf1dac266aab43884d82974a9adcccf"
        self.raw_recipient = "0x0000000000000000000000007ab6c736baf1dac266aab43884d82974a9adcccf"

        self.amount = 1709210771
        self.raw_amount = "0x0000000000000000000000000000000000000000000000000000000065e07c93"

        self.tx_hash = "0xa35cac639bd0f75e19bf28ceb26e60ddd057cce6e702769abb7b3e470300debd"
        self.event_entry = AttributeDict(
            {
                'args': AttributeDict(
                    {'from': self.sender,
                     'to': self.recipient,
                     'value': self.amount
                     }),
                'event': 'Transfer',
                'logIndex': 0,
                'transactionIndex': 0,
                'transactionHash': HexBytes(self.tx_hash),
                'address': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
                'blockHash': HexBytes('0xe87e98ac898edc2a8c811380f3be149ecf61e7d3ac4be1856df0724b2111f531'),
                'blockNumber': 392245
            }
        )
        self.raw_topics_with_amount_in_data = cast(LogReceipt, AttributeDict(
            {
                'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.raw_sender),
                    HexBytes(self.raw_recipient)],
                'data': HexBytes(self.raw_amount),
                'blockNumber': 44164819,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 4,
                'blockHash': HexBytes('0x3f5b3fa5038a372f4128a2bb72658393f5776b1257de1f64788a740cbea066c8'),
                'logIndex': 5,
                'removed': False
            }
        ))
        self.raw_topics_with_amount_in_topic = cast(LogReceipt, AttributeDict(
            {
                'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.raw_sender),
                    HexBytes(self.raw_recipient),
                    HexBytes(self.raw_amount),
                ],
                'data': HexBytes('0x'),
                'blockNumber': 44164819,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 4,
                'blockHash': HexBytes('0x3f5b3fa5038a372f4128a2bb72658393f5776b1257de1f64788a740cbea066c8'),
                'logIndex': 5,
                'removed': False
            }
        ))

    def test_should_create_model_instance_from_event_entry(self):
        token_transfers = FungibleTransferTransaction.from_event_entry(self.event_entry)
        self.assertEqual(1, len(token_transfers))
        token_transfer = token_transfers[0]
        model_instance = token_transfer.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        model_instance_from_database: TokenTransfer = TokenTransfer.objects.get()

        self.assertEqual(self.sender, model_instance_from_database.sender)
        self.assertEqual(self.recipient, model_instance_from_database.recipient)
        self.assertEqual(self.tx_hash, model_instance_from_database.tx_hash)
        self.assertEqual(self.amount, model_instance_from_database.amount)
        self.assertEqual(self.token, model_instance_from_database.token_instance)
        self.assertEqual(None, model_instance_from_database.token_id)

    def test_should_create_model_instance_from_raw_logs_with_amount_in_data(self):
        # noinspection PyTypeChecker
        transfer_transactions = FungibleTransferTransaction.from_raw_log(self.raw_topics_with_amount_in_data)
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.amount, model_instance.amount)
        self.assertEqual(None, model_instance.token_id)
        self.assertEqual(self.token, model_instance.token_instance)

    def test_should_create_model_instance_from_raw_logs_with_amount_in_topic(self):
        # noinspection PyTypeChecker
        transfer_transactions = FungibleTransferTransaction.from_raw_log(self.raw_topics_with_amount_in_topic)
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.amount, model_instance.amount)
        self.assertEqual(None, model_instance.token_id)
        self.assertEqual(self.token, model_instance.token_instance)

    def test_should_fail_when_no_enough_topics(self):
        transfer_transactions = FungibleTransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.raw_sender),
                ],
                'data': HexBytes('0x'),
                'blockNumber': 44164819,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 4,
                'blockHash': HexBytes('0x3f5b3fa5038a372f4128a2bb72658393f5776b1257de1f64788a740cbea066c8'),
                'logIndex': 5,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfer_transactions))

    def test_should_fail_when_bad_data(self):
        transfer_transactions = FungibleTransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.raw_sender),
                    HexBytes(self.raw_recipient),
                ],
                'data': HexBytes("0x"),
                'blockNumber': 44164819,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 4,
                'blockHash': HexBytes('0x3f5b3fa5038a372f4128a2bb72658393f5776b1257de1f64788a740cbea066c8'),
                'logIndex': 5,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfer_transactions))


# noinspection DuplicatedCode
class NonFungibleTransferTransactionTestCase(TestCase):
    network: Network
    token: Token

    sender: str
    sender_raw: str

    tx_hash: str

    recipient: str
    recipient_raw: str

    token_id: int
    token_id_raw: str

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Ethereum mainnet",
                                              rpc_url="https://ethereum.org",
                                              max_step=1000,
                                              type=NetworkType.filterable,
                                              need_poa=True)
        self.token = Token.objects.create(address="0x70757E9245940959a554B2d06EB765e08D8F3c37",
                                          name="NFT",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc721)
        self.sender = "0x0000000000000000000000000000000000000000"
        self.sender_raw = "0x0000000000000000000000000000000000000000000000000000000000000000"

        self.recipient = "0xc985b91ee461ea5cd76c6d131746c801097751dd"
        self.recipient_raw = "0x000000000000000000000000c985b91ee461ea5cd76c6d131746c801097751dd"

        self.token_id = 14176665
        self.token_id_raw = "0x0000000000000000000000000000000000000000000000000000000000d85199"

        self.tx_hash = "0x9a13e496abb52ddf8cdbec723df5c41c4004674a84939d042f807441d6159966"
        self.event_entry = AttributeDict(
            {
                'args': AttributeDict(
                    {
                        'from': self.sender,
                        'to': self.recipient,
                        'tokenId': self.token_id
                    }
                ),
                'event': 'Transfer',
                'logIndex': 511,
                'transactionIndex': 183,
                'transactionHash': HexBytes(self.tx_hash),
                'address': '0x9c614a8E5a23725214024d2C3633BE30D44806f9',
                'blockHash': HexBytes('0x6ec315db1d5bbfe1cd0230e793caf276d23e8fefe423f8a6f97f3ffdc7d747d5'),
                'blockNumber': 29263958
            }
        )
        self.raw_logs_with_token_id_in_topics = cast(LogReceipt, AttributeDict(
            {
                'address': '0x5D666F215a85B87Cb042D59662A7ecd2C8Cc44e6',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                    HexBytes(self.token_id_raw)],
                'data': HexBytes('0x'),
                'blockNumber': 44157100,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 40,
                'blockHash': HexBytes('0x3feefff29139236aa0a63a08a8037b01c50d0c2f71b950f6773b107be825c768'),
                'logIndex': 142,
                'removed': False
            }
        ))
        self.raw_logs_with_token_id_in_data = cast(LogReceipt, AttributeDict(
            {
                'address': '0x5D666F215a85B87Cb042D59662A7ecd2C8Cc44e6',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                ],
                'data': HexBytes(self.token_id_raw),
                'blockNumber': 44157100,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 40,
                'blockHash': HexBytes('0x3feefff29139236aa0a63a08a8037b01c50d0c2f71b950f6773b107be825c768'),
                'logIndex': 142,
                'removed': False
            }
        ))

    def test_should_create_model_instance_from_event_entry(self):
        transfer_transactions = NonFungibleTransferTransaction.from_event_entry(self.event_entry)
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        self.assertEqual(self.sender, model_instance.sender)
        self.assertEqual(self.recipient, model_instance.recipient)
        self.assertEqual(self.token_id, model_instance.token_id)
        self.assertEqual(None, model_instance.amount)
        self.assertEqual(self.token, model_instance.token_instance)

    def test_should_create_model_instance_from_raw_log_with_token_id_in_topics(self):
        # noinspection PyTypeChecker
        transfer_transactions = NonFungibleTransferTransaction.from_raw_log(self.raw_logs_with_token_id_in_topics)
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.token_id, model_instance.token_id)
        self.assertEqual(None, model_instance.amount)
        self.assertEqual(self.token, model_instance.token_instance)

    def test_should_create_model_instance_from_raw_log_with_token_id_in_data(self):
        # noinspection PyTypeChecker
        transfer_transactions = NonFungibleTransferTransaction.from_raw_log(self.raw_logs_with_token_id_in_data)
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.token_id, model_instance.token_id)
        self.assertEqual(None, model_instance.amount)
        self.assertEqual(self.token, model_instance.token_instance)

    def test_should_fail_when_bad_topics(self):
        # noinspection PyTypeChecker
        transfer_transactions = NonFungibleTransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x5D666F215a85B87Cb042D59662A7ecd2C8Cc44e6',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.sender_raw),
                ],
                'data': HexBytes('0x'),
                'blockNumber': 44157100,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 40,
                'blockHash': HexBytes('0x3feefff29139236aa0a63a08a8037b01c50d0c2f71b950f6773b107be825c768'),
                'logIndex': 142,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfer_transactions))

    def test_should_fail_when_bad_data(self):
        # noinspection PyTypeChecker
        transfer_transactions = NonFungibleTransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x5D666F215a85B87Cb042D59662A7ecd2C8Cc44e6',
                'topics': [
                    HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                ],
                'data': HexBytes("0x"),
                'blockNumber': 44157100,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 40,
                'blockHash': HexBytes('0x3feefff29139236aa0a63a08a8037b01c50d0c2f71b950f6773b107be825c768'),
                'logIndex': 142,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfer_transactions))


# noinspection DuplicatedCode
class ERC1155TransferTransactionTestCase(TestCase):
    network: Network
    token: Token

    operator: str
    operator_raw: str

    sender: str
    sender_raw: str

    tx_hash: str

    recipient: str
    recipient_raw: str

    single_amount: int
    single_amount_raw: str

    single_token_id: int
    single_token_id_raw: str

    single_transfer_data_raw: str

    transfer_batch_data_raw: str

    def setUp(self) -> None:
        self.network = Network.objects.create(chain_id=1,
                                              name="Ethereum mainnet",
                                              rpc_url="https://ethereum.org",
                                              max_step=1000,
                                              type=NetworkType.filterable,
                                              need_poa=True)
        self.token = Token.objects.create(address="0xE9975463EAc786C68bd095EE3Ed9Fbc75E0A7A8C",
                                          name="ERC1155",
                                          network=self.network,
                                          strategy=TokenStrategy.event_based_transfer,
                                          type=TokenType.erc1155)
        self.operator = "0x22e837c1e3380e8f38758c8490d9865433bf3ad5"
        self.operator_raw = "0x00000000000000000000000022e837c1e3380e8f38758c8490d9865433bf3ad5"

        self.sender = "0x0000000000000000000000000000000000000000"
        self.sender_raw = "0x0000000000000000000000000000000000000000000000000000000000000000"

        self.recipient = "0xc985b91ee461ea5cd76c6d131746c801097751dd"
        self.recipient_raw = "0x000000000000000000000000c985b91ee461ea5cd76c6d131746c801097751dd"

        self.single_transfer_data_raw = "0x00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000064"
        self.single_token_id = 1
        self.single_token_id_raw = "0x0000000000000000000000000000000000000000000000000000000000000001"

        self.single_amount = 100
        self.single_amount_raw = "0x0000000000000000000000000000000000000000000000000000000000000064"

        self.tx_hash = "0x9a13e496abb52ddf8cdbec723df5c41c4004674a84939d042f807441d6159966"

        self.transfer_single_raw_with_token_in_data = AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw)
                ],
                'data': HexBytes(self.single_transfer_data_raw),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 37,
                'removed': False
            }
        )

        self.transfer_single_raw_with_token_in_topics = AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                    HexBytes(self.single_token_id_raw),
                    HexBytes(self.single_amount_raw),
                ],
                'data': HexBytes("0x"),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 37,
                'removed': False
            }
        )

        self.transfer_batch_raw = AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw)
                ],
                'data': HexBytes(
                    '0x'
                    '0000000000000000000000000000000000000000000000000000000000000040'  # address of first array
                    '00000000000000000000000000000000000000000000000000000000000000c0'  # address of second array
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of first array
                    '0000000000000000000000000000000000000000000000000000000000000005'  # first element of first array
                    '0000000000000000000000000000000000000000000000000000000000000007'  # second element of first array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of first array
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of second array
                    '00000000000000000000000000000000000000000000000000000000000001f4'  # first element of second array
                    '00000000000000000000000000000000000000000000000000000000000002bc'  # second element of second array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of second array
                ),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 41,
                'removed': False
            }
        )
        self.token_ids = [5, 7, 0]
        self.amounts = [500, 700, 0]

    def test_should_create_token_transfer_from_single_erc1155_event_with_token_in_data(self):
        transfer_transactions = ERC1155TransferTransaction.from_raw_log(
            cast(LogReceipt, self.transfer_single_raw_with_token_in_data))
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()

        self.assertEqual(self.operator.lower(), str(model_instance.operator).lower())
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.single_token_id, model_instance.token_id)
        self.assertEqual(self.single_amount, model_instance.amount)

    def test_should_create_token_transfer_from_single_erc1155_event_with_token_in_topics(self):
        transfer_transactions = ERC1155TransferTransaction.from_raw_log(
            cast(LogReceipt, self.transfer_single_raw_with_token_in_topics))
        self.assertEqual(1, len(transfer_transactions))
        transfer_transaction = transfer_transactions[0]
        model_instance = transfer_transaction.to_token_transfer_model()
        model_instance.token_instance = self.token
        model_instance.save()

        self.assertEqual(self.operator.lower(), str(model_instance.operator).lower())
        self.assertEqual(self.sender.lower(), model_instance.sender.lower())
        self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        self.assertEqual(self.single_token_id, model_instance.token_id)
        self.assertEqual(self.single_amount, model_instance.amount)

    def test_should_create_many_token_transfer_from_batch_erc1155_event(self):
        transfer_transactions = ERC1155TransferTransaction.from_raw_log(
            cast(LogReceipt, self.transfer_batch_raw))
        self.assertEqual(3, len(transfer_transactions))
        for transfer_transaction in transfer_transactions:
            model_instance = transfer_transaction.to_token_transfer_model()
            model_instance.token_instance = self.token
            model_instance.save()
            self.assertEqual(self.operator.lower(), str(model_instance.operator).lower())
            self.assertEqual(self.sender.lower(), model_instance.sender.lower())
            self.assertEqual(self.recipient.lower(), model_instance.recipient.lower())
        tokens = TokenTransfer.objects.filter(tx_hash=self.tx_hash).values("token_id", "amount")
        token_ids: List[int] = []
        amounts: List[int] = []
        for token in tokens:
            if (token_id := token["token_id"]) is not None:
                token_ids.append(int(token_id))
            if (amount := token["amount"]) is not None:
                amounts.append(int(amount))
        self.assertEqual(self.token_ids, token_ids)
        self.assertEqual(self.amounts, amounts)

    def test_should_fail_single_transfer_when_bad_topics(self):
        transfers = ERC1155TransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                ],
                'data': HexBytes(self.single_transfer_data_raw),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 37,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfers))

    def test_should_fail_single_transfer_when_bad_data(self):
        transfers = ERC1155TransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                ],
                'data': HexBytes("0x"),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 37,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfers))

    def test_should_fail_batch_transfer_when_bad_topics(self):
        transfers = ERC1155TransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                ],
                'data': HexBytes(
                    '0x'
                    '0000000000000000000000000000000000000000000000000000000000000040'  # address of first array
                    '00000000000000000000000000000000000000000000000000000000000000c0'  # address of second array
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of first array
                    '0000000000000000000000000000000000000000000000000000000000000005'  # first element of first array
                    '0000000000000000000000000000000000000000000000000000000000000007'  # second element of first array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of first array
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of second array
                    '00000000000000000000000000000000000000000000000000000000000001f4'  # first element of second array
                    '00000000000000000000000000000000000000000000000000000000000002bc'  # second element of second array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of second array
                ),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 41,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfers))

    def test_should_fail_batch_transfer_when_bad_data(self):
        transfers = ERC1155TransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                ],
                'data': HexBytes(
                    '0x'
                ),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 41,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfers))

    def test_should_fail_batch_transfer_when_bad_address_in_data(self):
        transfers = ERC1155TransferTransaction.from_raw_log(cast(LogReceipt, AttributeDict(
            {
                'address': '0x9363bFCe94B1A51e0Bd1cc2B17B9D67D7AD29953',
                'topics': [
                    HexBytes('0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'),
                    HexBytes(self.operator_raw),
                    HexBytes(self.sender_raw),
                    HexBytes(self.recipient_raw),
                ],
                'data': HexBytes(
                    '0x'
                    '0000000000000000000000000000000000000000000000000000000000000040'  # address of first array
                    '00000000000000000000000000000000000000000000000000000001111111c0'  # BAD: address is overflow
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of first array
                    '0000000000000000000000000000000000000000000000000000000000000005'  # first element of first array
                    '0000000000000000000000000000000000000000000000000000000000000007'  # second element of first array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of first array
                    '0000000000000000000000000000000000000000000000000000000000000003'  # length of second array
                    '00000000000000000000000000000000000000000000000000000000000001f4'  # first element of second array
                    '00000000000000000000000000000000000000000000000000000000000002bc'  # second element of second array
                    '0000000000000000000000000000000000000000000000000000000000000000'  # third element of second array
                ),
                'blockNumber': 37142842,
                'transactionHash': HexBytes(self.tx_hash),
                'transactionIndex': 7,
                'blockHash': HexBytes('0x419b6535875a2e32939abaa32cd8a54b79dd48f0923ad89b9d6ec0fbf9142280'),
                'logIndex': 41,
                'removed': False
            }
        )))
        self.assertEqual(0, len(transfers))
