from setuptools import setup, find_packages
import ideadatamodel_meta

setup(
    name=ideadatamodel_meta.__name__,
    version=ideadatamodel_meta.__version__,
    description='API Data Models',
    url='https://awslabs.github.io/scale-out-computing-on-aws/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(exclude='tests'),
    package_dir={
        'ideadatamodel': 'ideadatamodel'
    }
)
