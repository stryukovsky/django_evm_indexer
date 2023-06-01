import math
from django.db import models

INT256_MAX_DIGITS = int(math.ceil(math.log10(2 ** 256)))
INT256_DECIMAL_PLACES = 0  # wei values has no decimal point
ETHEREUM_ADDRESS_LENGTH = 42
ETHEREUM_TX_HASH_LENGTH = 66
TX_HASH_LENGTH = 66
STRING_LENGTH = 255
DEFAULT_STEP = 1000
DEFAULT_LAST_BLOCK = 0


class NetworkType(models.TextChoices):
    filterable = "filterable"
    no_filters = "no_filters"


class TokenStrategy(models.TextChoices):
    event_based_transfer = "event_based_transfer"
    receipt_based_transfer = "receipt_based_transfer"


class IndexerStrategy(models.TextChoices):
    recipient = "recipient"
    sender = "sender"
    token_scan = "token_scan"
    tokenomics = "tokenomics"


class TokenType(models.TextChoices):
    native = "native"
    erc20 = "erc20"
    erc721 = "erc721"
    erc777 = "erc777"
    erc1155 = "erc1155"


FUNGIBLE_TOKENS = [TokenType.native, TokenType.erc20, TokenType.erc777]
NON_FUNGIBLE_TOKENS = [TokenType.erc721]
ERC1155_TOKENS = [TokenType.erc1155]


class Network(models.Model):
    chain_id = models.PositiveBigIntegerField()  # possibly there can be several instances of one network
    name = models.CharField(max_length=STRING_LENGTH)
    rpc_url = models.CharField(max_length=STRING_LENGTH * 10)  # possibly can store some token in it
    max_step = models.PositiveBigIntegerField(default=DEFAULT_STEP)
    type = models.CharField(max_length=STRING_LENGTH, choices=NetworkType.choices)
    need_poa = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.chain_id})"


class Indexer(models.Model):
    name = models.CharField(max_length=STRING_LENGTH, unique=True)  # must be unique since is used as identifier
    last_block = models.PositiveBigIntegerField(default=DEFAULT_LAST_BLOCK)
    network = models.ForeignKey(Network, related_name="indexers", on_delete=models.CASCADE)
    watched_tokens = models.ManyToManyField("Token", related_name="indexers")
    strategy = models.CharField(max_length=STRING_LENGTH, choices=IndexerStrategy.choices)
    short_sleep_seconds = models.PositiveBigIntegerField(default=1,
                                                         verbose_name="Short sleep is time between two filter requests to blockchain")
    long_sleep_seconds = models.PositiveBigIntegerField(default=5,
                                                        verbose_name="Indexer will sleep this time if no new blocks in blockchain by the moment")

    def __str__(self):
        return f"{self.name}"


class Token(models.Model):
    # not unique: possibly on several chains there can be tokens with the same address
    address = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True)
    name = models.CharField(max_length=STRING_LENGTH)
    strategy = models.CharField(choices=TokenStrategy.choices, max_length=STRING_LENGTH)
    network = models.ForeignKey(Network, related_name="tokens", on_delete=models.CASCADE)
    type = models.CharField(choices=TokenType.choices, max_length=STRING_LENGTH)

    total_supply = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES,
                                       default=0)
    volume = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, default=0)

    def __str__(self):
        return f"{self.name} ({self.address})"


class TokenBalance(models.Model):
    holder = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    token = models.ForeignKey(Token, related_name="balances", on_delete=models.CASCADE)

    amount: models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)
    token_id: models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True)


class TokenTransfer(models.Model):
    operator = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH, null=True, blank=True)
    sender = models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    recipient: models.CharField(max_length=ETHEREUM_ADDRESS_LENGTH)
    tx_hash: models.CharField(max_length=ETHEREUM_TX_HASH_LENGTH, unique=True)
    token_id = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                   blank=True)
    amount = models.DecimalField(max_digits=INT256_MAX_DIGITS, decimal_places=INT256_DECIMAL_PLACES, null=True,
                                 blank=True)
