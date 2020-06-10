import requests
import urllib.parse
from python_graphql_client import GraphqlClient
from datetime import datetime


class SlotGetter:
    def __init__(self, token, fulfilment_type, postcode):
        self.token = token
        self.fulfilment_type = fulfilment_type
        self.postcode = postcode

    def get_branches(self):
        r = requests.get(urllib.parse.quote_plus(f'https://www.waitrose.com/api/branch-prod/v3/branches?fulfilment_type=$self.fulfilment_type&location=$self.postcode'))
        return r.content

    def get_last_address_id(self):
        r = requests.get('https://www.waitrose.com/api/address-prod/v1/addresses?sortBy=-lastDelivery', headers={'authorization': f"Bearer {self.token}"}).json()
        return r[0]['id']

    def get_slots(self, branch_id, customer_order_id):
        client = GraphqlClient(endpoint="https://www.waitrose.com/api/graphql-prod/graph/live")

        # Create the query string and variables required for the request.
        query = """
            query slotDays($slotDaysInput: SlotDaysInput) {  
                slotDays(slotDaysInput: $slotDaysInput) {
                    content {
                        id
                        branchId
                        slotType
                        date
                        slots {
                            slotId: id
                            startDateTime
                            endDateTime
                            shopByDateTime
                            slotStatus: status
                        }
                    }
                    links {
                        rel
                        title
                        href
                    }
                    failures {
                        message
                        type
                    }
                }
            }
        """

        variables = {"slotDaysInput": {
            "branchId": branch_id,
            "slotType": self.fulfilment_type,
            "customerOrderId": customer_order_id,
            "addressId": self.get_last_address_id(),
            "fromDate": datetime.today().strftime('%Y-%m-%d'),
            "size": 5
        }}

        return client.execute(query=query, variables=variables, headers={'authorization': f"Bearer {self.token}"})

    def get_available_slots(self, branch_id, customer_order_id):
        res = set()
        slot_days = self.get_slots(branch_id=branch_id, customer_order_id=customer_order_id)
        for sd in slot_days['data']['slotDays']['content']:
            for s in sd['slots']:
                if s['slotStatus'] not in ('FULLY_BOOKED', 'UNAVAILABLE'):
                    res.add(s['slotId'])
        return res
