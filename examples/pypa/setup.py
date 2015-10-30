from setuptools import setup, find_packages

setup(
    name='bacula_monitor',
    version='1.0',
    long_description=__doc__,
    packages=find_packages( exclude=[ 'archiv', '*.pyc' ] ),
    include_package_data=True,
    zip_safe=False,
    install_requires=['Django', 'psycopg2'],
)
