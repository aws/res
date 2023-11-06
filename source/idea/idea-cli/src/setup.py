from setuptools import setup, find_packages
import ideacli_meta

setup(
    name=ideacli_meta.__name__,
    version=ideacli_meta.__version__,
    description='CLIs',
    url='https://awslabs.github.io/scale-out-computing-on-aws/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    include_package_data=True,
    entry_points='''
        [console_scripts]
        soca=ideacli.soca:main
    '''
)
