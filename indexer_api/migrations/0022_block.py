# Generated by Django 4.2.1 on 2023-06-20 09:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indexer_api', '0021_tokentransfer_event_date_alter_indexer_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.DecimalField(decimal_places=0, max_digits=78)),
                ('date', models.DateTimeField()),
                ('network', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='indexer_api.network')),
            ],
        ),
    ]
