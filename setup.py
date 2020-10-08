from setuptools import find_packages, setup

setup(
    name="core",
    version="0.0.1a0",
    description="Optuna core",
    packages=find_packages(),
    install_requires=["numpy"],
)
