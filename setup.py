from setuptools import find_packages, setup

version = '4.0.0'

setup(
    name='zabbix-alerta',
    version=version,
    description='Forward Zabbix events to Alerta',
    url='https://github.com/alerta/zabbix-alerta',
    license='MIT',
    author='Nick Satterly',
    author_email='nick.satterly@gmail.com',
    packages=find_packages(),
    py_modules=['zabbix_alerta', 'zabbix_config'],
    install_requires=[
        'alerta>=5.0.2',
        'Click',
        'pyzabbix',
        'protobix'
    ],
    include_package_data=True,
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'zabbix-alerta = zabbix_alerta:cli',
            'zac = zabbix_config:main'
        ]
    },
    keywords='alert monitoring zabbix',
    classifiers=[
        'Topic :: System :: Monitoring'
    ],
    python_requires='>=3.6'
)
