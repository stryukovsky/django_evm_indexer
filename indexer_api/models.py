import math
from typing import Optional

from django.db import models
from django.core.validators import RegexValidator, URLValidator
from django.core.exceptions import ValidationError
from indexer_api.validators import validate_explorer_url, is_ethereum_address_valid, validate_ethereum_address

INT256_MAX_DIGITS = int(math.ceil(math.log10(2 ** 256)))
INT256_DECIMAL_PLACES = 0  # wei values has no decimal point
ETHEREUM_ADDRESS_LENGTH = 42
ETHEREUM_TX_HASH_LENGTH = 66
TX_HASH_LENGTH = 66
STRING_LENGTH = 255
DEFAULT_STEP = 1000
DEFAULT_LAST_BLOCK = 0


class NetworkType(models.TextChoices):
    filterable = ("filterable", "Filterable eth_filter")
    no_filters = ("no_filters", "No filters supported")


class TokenStrategy(models.TextChoices):
    event_based_transfer = ("event_based_transfer", "Event-based transfers")
    receipt_based_transfer = ("receipt_based_transfer", "Receipt-based transfers")


class IndexerStrategy(models.TextChoices):
    recipient = ("recipient", "Recipient")
    sender = ("sender", "Sender")
    token_scan = ("token_scan", "Scan transfers (all transfers are saved)")
    tokenomics = ("tokenomics", "Tokenomics parameters")
    specified_holders = ("specified_holders", "Specified holders")
    transfers_participants = ("transfers_participants", "Transfer participants")


TRANSFER_INDEXER_STRATEGIES = (IndexerStrategy.recipient, IndexerStrategy.sender, IndexerStrategy.token_scan,)
BALANCE_INDEXER_STRATEGIES = (IndexerStrategy.specified_holders, IndexerStrategy.transfers_participants,)


class TokenType(models.TextChoices):
    native = ("native", "Native")
    erc20 = ("erc20", "ERC20 Fungible token")
    erc721 = ("erc721", "NFT ERC721")
    erc721enumerable = ("erc721enumerable", "NFT ERC721Enumerable")
    erc777 = ("erc777", "ERC777 Fungible token")
    erc1155 = ("erc1155", "ERC1155 collection token")


class IndexerType(models.TextChoices):
    transfer_indexer = ("transfer_indexer", "Transfer indexer")
    balance_indexer = ("balance_indexer", "Balance indexer")


class IndexerStatus(models.TextChoices):
    on = ("on", "Active")
    off = ("off", "Disabled")


FUNGIBLE_TOKENS = [TokenType.native, TokenType.erc20, TokenType.erc777]
NON_FUNGIBLE_TOKENS = [TokenType.erc721, TokenType.erc721enumerable]
ERC1155_TOKENS = [TokenType.erc1155]


class Network(models.Model):
    chain_id = models.PositiveBigIntegerField(unique=True)
    name = models.CharField(max_length=STRING_LENGTH)
    # possibly can store some token in it
    rpc_url = models.CharField(max_length=STRING_LENGTH * 10, validators=[URLValidator(schemes=("http", "https"))],
                               help_text="URL must contain schema (http or https) and port")
    max_step = models.PositiveBigIntegerField(default=DEFAULT_STEP)
    type = models.CharField(max_length=STRING_LENGTH, choices=NetworkType.choices)
    need_poa = models.BooleanField(default=False)
    # possibly can store some token in it
    explorer_url = models.CharField(max_length=STRING_LENGTH * 10, default="", blank=True,
                                    validators=[URLValidator(schemes=("http", "https")), validate_explorer_url],
                                    help_text="Provide root URL of explorer with no trailing slash. Example: 'https://etherscan.io'")

    def __str__(self):
        return f"{self.name} ({self.chain_id})"


class Indexer(models.Model):
    name = models.CharField(max_length=STRING_LENGTH, unique=True, validators=[
        RegexValidator(regex="^[a-z]{1}[a-z0-9-]+$",
                       message="Name should be a valid Docker container name in format my-indexer-name")],
                            help_text="Name should be a valid container identifier. Example: <code>polygon-mainnet-usdt-tracker</code>")  # must be unique since is used as identifier
    last_block = models.PositiveBigIntegerField(default=DEFAULT_LAST_BLOCK)
    network = models.ForeignKey(Network, related_name="indexers", on_delete=models.CASCADE)
    watched_tokens = models.ManyToManyField("Token", related_name="indexers")
    strategy = models.CharField(max_length=STRING_LENGTH, choices=IndexerStrategy.choices)
    short_sleep_seconds = models.PositiveBigIntegerField(default=1,
                                                         help_text="Short sleep is time between two filter requests to blockchain")
    long_sleep_seconds = models.PositiveBigIntegerField(default=5,
                                                        help_text="Indexer will sleep this time if no new blocks in blockchain by the moment")
    strategy_params = models.JSONField(verbose_name="Configure indexer's strategy using JSON dict", null=True,
                                       blank=True)

    status = models.CharField(max_length=STRING_LENGTH, choices=IndexerStatus.choices, default=IndexerStatus.off)
    type = models.CharField(max_length=STRING_LENGTH, choices=IndexerType.choices, default=IndexerType.transfer_indexer)

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        super().full_clean(exclude, validate_unique, validate_constraints)
        match self.type:
            case IndexerType.transfer_indexer:
                self.validate_transfer_indexer_strategy(self.strategy)
            case IndexerType.balance_indexer:
                self.validate_balance_indexer_strategy(self.strategy)
        match self.strategy:
            case IndexerStrategy.sender:
                self.validate_sender_strategy_params(self.strategy_params)
            case IndexerStrategy.recipient:
                self.validate_recipient_strategy_params(self.strategy_params)
            case IndexerStrategy.specified_holders:
                self.validate_specified_holders_strategy_params(self.strategy_params)

    @staticmethod
    def validate_transfer_indexer_strategy(strategy: str):
        if strategy not in TRANSFER_INDEXER_STRATEGIES:
            raise ValidationError(
                f"Indexer has bad strategy! Transfer indexer may have strategies: {','.join(map(lambda x: x.label, TRANSFER_INDEXER_STRATEGIES))}")

    @staticmethod
    def validate_balance_indexer_strategy(strategy: str):
        if strategy not in BALANCE_INDEXER_STRATEGIES:
            raise ValidationError(
                f"Indexer has bad strategy! Balance indexer may have strategies: {', '.join(map(lambda x: x.label, BALANCE_INDEXER_STRATEGIES))}")

    @staticmethod
    def validate_sender_strategy_params(strategy_params: dict):
        if not (sender := strategy_params.get("sender")):
            raise ValidationError("Bad sender strategy: no sender specified in JSON params")
        if not is_ethereum_address_valid(sender):
            raise ValidationError("Bad sender strategy: sender in JSON strategy params is malformed")

    @staticmethod
    def validate_recipient_strategy_params(strategy_params: dict):
        if not (recipient := strategy_params.get("recipient")):
            raise ValidationError("Bad recipient strategy: no recipient specified in JSON params")
        if not is_ethereum_address_valid(recipient):
            raise ValidationError("Bad recipient strategy: recipient in JSON strategy params is malformed")

    def __str__(self):
        return f"{self.name}"

    @staticmethod
    def validate_specified_holders_strategy_params(strategy_params: dict):
        if not strategy_params:
            raise ValidationError("Bad specified holders strategy: no params JSON provided")
        if not (holders := strategy_params.get("holders")):
            raise ValidationError("Bad specified holders strategy: strategy params JSON has no holders")
        if type(holders) != list:
            raise ValidationError("Bad specified holders strategy: strategy params JSON has non-array holders")
        for holder in holders:
            if not is_ethereum_address_valid(holder):
                raise ValidationError(
                    f"Bad specified holders strategy: specified holder {holder} is not an ethereum address")


class Token(models.Model):
    # not unique: possibly on several chains there can be tokens with the same address
    address = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True,
                               validators=[validate_ethereum_address],
                               help_text="Provide a valid 20-byte Ethereum address with <code>0x</code> prefix. <br>"
                                         "For native token leave this field empty")
    name = models.CharField(max_length=STRING_LENGTH, help_text="Several tokens may have the same name")
    strategy = models.CharField(choices=TokenStrategy.choices, max_length=STRING_LENGTH,
                                help_text="Use Receipt-based transfer strategy only with native token. <b>Note</b>: it can be very slow to index. "
                                          "<br> Use Event-based transfers for all other token types.")
    network = models.ForeignKey(Network, related_name="tokens", on_delete=models.CASCADE,
                                help_text="Network where this token is already deployed")
    type = models.CharField(choices=TokenType.choices, max_length=STRING_LENGTH,
                            help_text="Options NFT ERC721 and NFT ERC721Enumerable are the same when only transfers will be tracked.<br>"
                                      "When balances are indexed, NFT ERC721Enumerable is a better option than ERC721 since it allows to see exact owned token ids. <br>"
                                      "Note: make sure contract implements <code>ERC721Enumerable</code> before marking token as NFT ERC721Enumerable")

    total_supply = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES,
                                       default=0)
    volume = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, default=0)

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        super().full_clean(exclude, validate_unique, validate_constraints)
        match self.type:
            case TokenType.native:
                self.validate_native_token_strategy(self.strategy)
                self.validate_native_token_address(self.address)
            case _:
                self.validate_other_token_strategy(self.strategy)
                self.validate_other_token_address(self.address)

    def __str__(self):
        return f"{self.name} on {self.network.name}"

    class Meta:
        unique_together = [["address", "network"]]

    @staticmethod
    def validate_native_token_strategy(strategy):
        if strategy != TokenStrategy.receipt_based_transfer:
            raise ValidationError("Token strategy: native tokens can be tracked only with Receipt-based strategy")

    @staticmethod
    def validate_other_token_strategy(strategy):
        if strategy != TokenStrategy.receipt_based_transfer:
            raise ValidationError("Token strategy: non-native tokens should be tracked with Event-based strategy")

    @staticmethod
    def validate_native_token_address(address: Optional[str]):
        if address is not None:
            raise ValidationError("Native token address should be null. Leave address field empty")

    @staticmethod
    def validate_other_token_address(address):
        if address is None:
            raise ValidationError("Non-native token must have address")


class TokenBalance(models.Model):
    holder = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, validators=[validate_ethereum_address])
    token_instance = models.ForeignKey(Token, related_name="balances", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)
    token_id = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)

    def __str__(self):
        return f"Balance of {self.holder} on {self.token_instance.address}"

    class Meta:
        verbose_name = "Balance"


class TokenTransfer(models.Model):
    token_instance = models.ForeignKey(Token, related_name="transfers", on_delete=models.CASCADE)
    operator = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True)
    sender = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, validators=[validate_ethereum_address])
    recipient = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, validators=[validate_ethereum_address])
    tx_hash = models.CharField(max_length=ETHEREUM_TX_HASH_LENGTH, unique=True)
    token_id = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                   blank=True)
    amount = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                 blank=True)

    class Meta:
        verbose_name = "Transfer"

    def __str__(self):
        return f"{self.token_instance.name} transfer {self.sender} → {self.recipient}"
