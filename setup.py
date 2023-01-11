#
import setuptools
from setuptools import setup


metadata = {'name': 'oaiv',
            'maintainer': 'Edward Azizov',
            'maintainer_email': 'edazizovv@gmail.com',
            'description': 'Blockchain Interaction Library',
            'license': 'MIT',
            'url': 'https://github.com/edazizovv/oaiv',
            'download_url': 'https://github.com/edazizovv/oaiv',
            'packages': setuptools.find_packages(),
            'include_package_data': True,
            'version': '0.11.7',
            'long_description': '',
            'python_requires': '>=3.10',
            'install_requires': []}

setup(**metadata)
