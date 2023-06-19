import dataclasses
from typing import Dict

from indexer_api.models import Indexer, IndexerStatus, TokenTransfer, IndexerType, TokenBalance


@dataclasses.dataclass
class IndexerMetrics:
    indexers_on: int
    indexers_off: int
    total_indexers: int
    transfers_fetched_total: int
    transfers_fetched: Dict
    balances_tracked: Dict

    def __init__(self):
        self.indexers_on = Indexer.objects.filter(status=IndexerStatus.on).count()
        self.indexers_off = Indexer.objects.filter(status=IndexerStatus.off).count()
        indexers = Indexer.objects.all()
        self.total_indexers = indexers.count()
        self.transfers_fetched_total = TokenTransfer.objects.all().count()
        self.transfers_fetched = {}
        self.balances_tracked = {}
        for indexer in indexers:
            match indexer.type:
                case IndexerType.transfer_indexer:
                    self.transfers_fetched[indexer.name] = TokenTransfer.objects.filter(fetched_by=indexer).count()
                case IndexerType.balance_indexer:
                    self.balances_tracked[indexer.name] = TokenBalance.objects.filter(tracked_by=indexer).count()

    def to_prometheus_metrics(self) -> str:
        metrics = self.__dict__
        result = []
        for key in metrics:
            value = metrics[key]
            if type(value) is int:
                result.append(f"{key} {value}")
            elif type(value) is dict:
                dict_metric = dict(value)
                for label in dict_metric:
                    result.append(str(key) + "{label=" + str(label) + "} " + str(dict_metric[label]))
        return "\n".join(result)
