#
import json
import datetime

#
from web3 import Web3
from urllib import parse, request

#
from oaiv.tools.utils import format_provider, format_w3, data_constructor, check_precision
from oaiv.tools.address import find_address


class InteractionFunctionality:
    def __init__(self, etherscan_api_key, ethereum_network, infura_project_id):
        self.network = ethereum_network
        self.etherscan_api_key = etherscan_api_key
        self.provider = format_provider(
            ethereum_network=ethereum_network,
            infura_project_id=infura_project_id
        )
        self.w3 = format_w3(provider=self.provider)

        self.etherscan = EtherscanInteraction(
            network=ethereum_network,
            etherscan_api_key=etherscan_api_key
        )
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
        network = {
            'mainnet': 'https://api.etherscan.io/api',
            'goerli': 'https://api-goerli.etherscan.io/api',
            'ropsten': 'https://api-ropsten.etherscan.io/api'
        }
        try:
            url = network[self.network]
        except KeyError:
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

    def get_transactions(self, account, sort='desc', raw=True):
        re = tuple()
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
        response_data_eth = self.request(params)
        if not raw:
            results_eth = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [], 'currency': []}
            for item in response_data_eth['result']:
                results_eth['tx'].append(item['hash'])
                results_eth['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_eth['sender'].append(item['from'])
                results_eth['receiver'].append(item['to'])
                results_eth['value'].append(float(Web3.fromWei(number=int(item['value']), unit='ether')))
                results_eth['commission_paid'].append(float(Web3.fromWei(number=(int(item['gasPrice']) * int(item['gasUsed'])), unit='ether')))
                results_eth['currency'].append('ETH')
            re += (results_eth,)
        else:
            re += (response_data_eth,)
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': account,
            # &contractaddress=0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2  # we can use this arg to filter by spec token
            'startblock': 0,  # check numbers
            'endblock': 99999999,  # TODO: check numbers
            # 'page': 1,
            # 'offset': 10,
            'sort': sort,
            'apikey': self.etherscan_api_key,
        }
        response_data_erc20 = self.request(params)
        # TODO: fix the Decimal issue
        if not raw:
            results_erc20 = {'tx': [], 'datetime': [], 'sender': [], 'receiver': [], 'value': [], 'commission_paid': [], 'currency': []}
            for item in response_data_erc20['result']:
                results_erc20['tx'].append(item['hash'])
                results_erc20['datetime'].append(datetime.datetime.fromtimestamp(int(item['timeStamp'])))
                results_erc20['sender'].append(item['from'])
                results_erc20['receiver'].append(item['to'])
                results_erc20['value'].append(int(item['value']) / (10 ** int(item['tokenDecimal'])))
                results_erc20['commission_paid'].append(float(Web3.fromWei(number=(int(item['gasPrice']) * int(item['gasUsed'])), unit='ether')))
                results_erc20['currency'].append(item['tokenSymbol'])
            re += (results_erc20,)
        else:
            re += (response_data_erc20,)
        return re


# TODO: add mnemonic support (see the w3.eth.account docs)
# TODO: add importing & exporting features
class Actor:
    def __init__(self, w3, private_key=None, address=None, encryption=None):
        self.w3 = w3
        self.private_key = private_key
        if private_key:
            self.account = w3.eth.account.from_key(private_key)
        else:
            self.account = None
        if address:
            if w3.isChecksumAddress(address):
                self._address = address
            else:
                self._address = self.w3.toChecksumAddress(address)
        self.encryption = encryption

    @property
    def nonce(self):
        return self.w3.eth.get_transaction_count(self.address)

    @property
    def address(self):
        if self.account:
            return self.account.address
        else:
            return self._address

    def sign_transaction(self, tx):
        if self.private_key:
            return self.account.sign_transaction(tx)
        else:
            raise Exception("You have to provide a private_key to use this feature")


class InfuraInteraction:
    def __init__(self, w3):
        self.w3 = w3

    # TODO: add mnemonic support (see the w3.eth.account docs)
    def create_account(self):
        private_key = self.w3.eth.account.create().key.hex()
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
                token_contract_address = find_address(name=currency)
                contract = Actor(w3=self.w3, private_key=None, address=token_contract_address)
                tx['to'] = contract.address
                tx['data'] = data_constructor(
                    receiver_address=receiver.address,
                    amount=value,
                    currency=currency
                )

        # TODO: improve gas calculations with pre-London and post-London versions
        if gas:
            tx['gas'] = gas
        else:
            tx['gas'] = self.w3.eth.estimate_gas(tx)

        tx['gasPrice'] = self.w3.eth.gasPrice
        tx['nonce'] = sender.nonce

        return tx

    def make_transaction(self, sender, receiver, value=None, currency=None, gas=None):
        tx = self.generate_transaction_data(
            sender=sender,
            receiver=receiver,
            value=value,
            currency=currency,
            gas=gas
        )

        signed_txn = sender.sign_transaction(tx)

        tx_id = self.w3.toHex(self.w3.eth.sendRawTransaction(signed_txn.rawTransaction))

        return tx_id
