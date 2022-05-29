#
import json


#
from urllib import parse, request


#
from oaiv.tools.utils import format_provider, format_w3, data_constructor, check_precision
from oaiv.tools.address import find_address


#
class InteractionFunctionality:

    def __init__(self, etherscan_api_key, ethereum_network, infura_project_id):

        self.network = ethereum_network
        self.etherscan_api_key = etherscan_api_key
        self.provider = format_provider(ethereum_network=ethereum_network, infura_project_id=infura_project_id)
        self.w3 = format_w3(provider=self.provider)

        self.etherscan = EtherscanInteraction(network=ethereum_network, etherscan_api_key=etherscan_api_key)
        self.infura = InfuraInteraction(w3=self.w3)

    def balance(self, **kwargs):

        return self.etherscan.balance(**kwargs)

    def get_transactions(self, **kwargs):

        return self.etherscan.get_transactions(**kwargs)

    def create_account(self):

        return self.infura.create_account()

    def make_transaction(self, **kwargs):

        return self.infura.make_transaction(**kwargs)


class EtherscanInteraction:

    def __init__(self, network, etherscan_api_key):
        self.network = network
        self.etherscan_api_key = etherscan_api_key

    def request(self, params):
        if self.network == 'mainnet':
            url = 'https://api.etherscan.io/api'
        elif self.network == 'goerli':
            url = 'https://api-goerli.etherscan.io/api'
        elif self.network == 'ropsten':
            url = 'https://api-ropsten.etherscan.io/api'
        else:
            raise KeyError("Invalid network name")
        query = parse.urlencode(params)
        url = '{0}?{1}'.format(url, query)
        with request.urlopen(url) as response:
            response_data = json.loads(response.read())

        return response_data

    def balance(self, address, currency, status='latest', contract_address=None):

        if status not in ['latest', 'pending']:
            raise KeyError("Invalid status value. Please provide 'latest' or 'pending' status value.")
        if (contract_address is None) and (currency != 'ETH'):
            contract_address = find_address(name=currency)

        if currency == 'ETH':
            params = {
                'module': 'account',
                'action': 'balance',
                'address': address,
                'tag': status,
                'apikey': self.etherscan_api_key,
            }
        else:
            params = {
                'module': 'account',
                'action': 'tokenbalance',
                'contractaddress': contract_address,
                'address': address,
                'tag': status,
                'apikey': self.etherscan_api_key,
            }

        response_data = self.request(params)

        # TODO: fix the Decimal issue
        if response_data['message'] == 'OK':
            if currency == 'ETH':
                precision = 18
            else:
                precision = check_precision(currency)
            result = int(response_data['result']) / (10 ** precision)
        else:
            raise Exception("{0}".format(response_data))

        return result

    def get_transactions(self, account, sort='desc'):

        params = {
            'module': 'account',
            'action': 'txlist',
            'address': account,
            'startblock': 0,  # check numbers
            'endblock': 99999999,  # TODO: check numbers
            # 'page': 1,
            # 'offset': 10,
            'sort': sort,
            'apikey': self.etherscan_api_key,
        }
        response_data = self.request(params)
        return response_data


# TODO: add mnemonic support (see the w3.eth.account docs)
# TODO: add importing & exporting features
class Actor:
    def __init__(self, w3, private_key=None, public_key=None, encryption=None):
        self.w3 = w3
        self.private_key = private_key
        if private_key:
            self.account = w3.eth.account.from_key(private_key)
        else:
            self.account = None
        self.public_key = public_key
        self.encryption = encryption

    @property
    def nonce(self):
        return self.w3.eth.get_transaction_count(self.address)

    @property
    def address(self):
        if self.account:
            return self.account.address
        else:
            return self.w3.toChecksumAddress(self.public_key)

    def sign_transaction(self, tx):
        if self.private_key:
            return self.account.sign_transaction(tx)
        else:
            raise Exception("You have to provide private_key to use this feature")


class InfuraInteraction:

    def __init__(self, w3):

        self.w3 = w3

    # TODO: add mnemonic support (see the w3.eth.account docs)
    def create_account(self):
        private_key = self.w3.eth.account.create().key
        actor = Actor(w3=self.w3, private_key=private_key)
        return actor

    def generate_transaction_data(self, sender, receiver, value=None, currency=None, gas=None):

        tx = {
            'from': sender.address,
            'to': receiver.address,
        }

        if value:
            if currency == 'ETH':
                tx['value'] = self.w3.toWei(value, 'ether')
            else:
                tx['data'] = data_constructor(receiver_address=receiver.address, amount=value, currency=currency)

        # TODO: improve gas calculations with pre-London and post-London versions
        if gas:
            tx['gas'] = gas
        else:
            tx['gas'] = self.w3.eth.estimate_gas(tx)

        tx['gasPrice'] = self.w3.eth.gasPrice
        tx['nonce'] = sender.nonce

        return tx

    def make_transaction(self, sender, receiver, value=None, currency=None, gas=None):

        tx = self.generate_transaction_data(sender=sender, receiver=receiver,
                                            value=value, currency=currency, gas=gas)

        signed_txn = sender.sign_transaction(tx)

        tx_id = self.w3.toHex(self.w3.eth.sendRawTransaction(signed_txn.rawTransaction))

        return tx_id
