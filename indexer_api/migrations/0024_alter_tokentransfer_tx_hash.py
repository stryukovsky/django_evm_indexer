# Generated by Django 4.2.1 on 2023-06-22 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indexer_api', '0023_remove_tokentransfer_event_date_delete_block'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tokentransfer',
            name='tx_hash',
            field=models.CharField(max_length=66),
        ),
    ]
