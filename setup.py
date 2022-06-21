import re
from pathlib import Path

from setuptools import setup

packages = [
    'github',
]

extras_require = {
    'docs': [
        'sphinx==4.4.0',
        'sphinxcontrib_trio==1.1.2',
        'sphinxcontrib-websupport',
        'typing-extensions',
    ],
}

setup(
    name='github',
    author='VarMonke & sudosnok',
    url='https://github.com/VarMonke/Github-Api-Wrapper',
    version=re.search(r'\d[.]\d[.]\d', (Path('github') / '__init__.py').read_text())[0],
    packages=packages,
    license='MIT',
    description='An asynchronous python wrapper around the GitHub API',
    long_description=Path('README.rst').read_text(),
    install_requires=Path('requirements.txt').read_text().splitlines(),
    python_requires='>=3.8.0',
)
