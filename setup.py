from setuptools import setup, find_packages, Extension

setup(
    name='pyestate',
    version='0.0.1',
    author='Andrew Barisser',
    license='MIT',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'pandas'
        ],
    tests_require=['pytest-cov', 'pytest'])