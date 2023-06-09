# Generated by Django 4.2.1 on 2023-06-15 06:17

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indexer_api', '0017_alter_indexer_name_alter_token_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='network',
            name='chain_id',
            field=models.PositiveBigIntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name='network',
            name='rpc_url',
            field=models.CharField(help_text='URL must contain schema (http or https) and port', max_length=2550, validators=[django.core.validators.URLValidator(schemes=('http', 'https'))]),
        ),
        migrations.AlterField(
            model_name='token',
            name='address',
            field=models.CharField(blank=True, help_text='Provide a valid 20-byte Ethereum address with <code>0x</code> prefix', max_length=42, null=True, validators=[django.core.validators.RegexValidator(regex='^0x[a-fA-F0-9]{40}$')]),
        ),
        migrations.AlterField(
            model_name='token',
            name='name',
            field=models.CharField(help_text='Several tokens may have the same name', max_length=255),
        ),
        migrations.AlterField(
            model_name='token',
            name='network',
            field=models.ForeignKey(help_text='Network where this token is already deployed', on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='indexer_api.network'),
        ),
        migrations.AlterField(
            model_name='token',
            name='strategy',
            field=models.CharField(choices=[('event_based_transfer', 'Event-based transfers'), ('receipt_based_transfer', 'Receipt-based transfers')], help_text='Use Receipt-based transfer strategy only with native token. <b>Note</b>: it can be very slow to index. <br> Use Event-based transfers for all other token types', max_length=255),
        ),
        migrations.AlterField(
            model_name='token',
            name='type',
            field=models.CharField(choices=[('native', 'Native'), ('erc20', 'ERC20 Fungible token'), ('erc721', 'NFT ERC721'), ('erc721enumerable', 'NFT ERC721Enumerable'), ('erc777', 'ERC777 Fungible token'), ('erc1155', 'ERC1155 collection token')], help_text='Options NFT ERC721 and Enumerable are the same if token is indexed only by transfers (not balances).<br>On indexing balances, NFT ERC721Enumerable is a better option than plain one since it allows to see exact owned token ids', max_length=255),
        ),
    ]
