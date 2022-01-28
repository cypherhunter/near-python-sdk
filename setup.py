"""
Near-python-sdk
-------------
Easily serve your static files from aliyun oss.
"""
from setuptools import setup


__version__ = "0.0.1"


setup(
    name="Near-python-sdk",
    version=__version__,
    url="https://github.com/ExchangeAnn/near-python-sdk",
    license="MIT",
    author="jiaxin",
    author_email="edison7500@gmail.com",
    description="Seamlessly serve the static files of your Flask app from aliyun oss",
    long_description=__doc__,
    py_modules=["near"],
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
