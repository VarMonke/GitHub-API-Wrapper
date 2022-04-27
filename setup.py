from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

version = '1.0.0'

packages = [
    'Github',
]

readme = ''
with open('README.md') as f:
    readme = f.read()

setup(
    name='Github',
    author='VarMonke & sudosnok',
    url='https://github.com/VarMonke/Github-Api-Wrapper',
    version=version,
    packages=packages,
    license='MIT',
    description='An asynchronous python wrapper around the GitHub API',
    long_description=readme,
    install_requires=requirements,
    python_requires='>=3.8.0',
)