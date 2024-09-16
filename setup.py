"""
Near-python-sdk
-------------
Easily fetch blockchain data for near
"""
from setuptools import setup

__version__ = "0.0.3"

setup(
    name="near-python-sdk",
    version=__version__,
    url="https://github.com/ExchangeAnn/near-python-sdk",
    license="MIT",
    author="jiaxin",
    author_email="muck-endorse-anvil@duck.com",
    description="Fetch blockchain data for Near-Protocol",
    long_description=__doc__,
    packages=["near"],
    zip_safe=False,
    include_package_data=True,
    platforms="near",
    install_requires=["requests>=2.25"],
    classifiers=[
        "Environment :: Python Environment",
        "Intended Audience :: Developers",
        "License :: MIT License",
        "Operating System :: Near Protocol BlockChain",
        "Programming Language :: Python",
        "Topic :: BlockChain :: Near-Protocol",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
