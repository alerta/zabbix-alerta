
from setuptools import setup, find_packages

version = '3.2.0'

setup(
    name="zabbix-alerta",
    version=version,
    description='Forward Zabbix events to Alerta',
    url='https://github.com/alerta/zabbix-alerta',
    license='MIT',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=find_packages(),
    py_modules=['zabbix_alerta'],
    install_requires=[
        'alerta'
    ],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'zabbix-alerta = zabbix_alerta:main'
        ]
    },
    keywords='alert monitoring zabbix',
    classifiers=[
        'Topic :: System :: Monitoring'
    ]
)
