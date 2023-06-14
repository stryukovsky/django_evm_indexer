from django.test import TestCase

from indexer_api.models import Network


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
