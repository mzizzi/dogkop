#!/usr/bin/env python
from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='dogkop',
        version='0.0.0a0',
        author='Matthew Zizzi',
        author_email='mhzizzi@gmail.com',
        keywords=['kubernetes', 'operator', 'datadog', 'python', 'k8s'],
        packages=find_packages(),
        install_requires=[
            'kopf',
            'datadog'
        ],
    )
