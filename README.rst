Github API Wrapper(Development on hold till May 2025)
==================

Please note that development is currently on hold until May 2025. As I am in the final year of my studies, I am unable to actively maintain this project at the moment. However, I plan to resume development as soon as possible. Upon reviewing the code recently, I identified several redundancies and areas that could benefit from significant improvement, which I intend to address once development resumes.

.. image:: https://discord.com/api/guilds/963406460107235328/widget.png
  :target: https://discord.gg/DWhwsQ5TsT
  :alt: Discord Server Invite

Easy to use Python wrapper for the **Github API**.

Key Features
------------
- Modern Pythonic Interface
- Easy to use


Installing
----------

**Python 3.8 or higher is required to run the library**

To install the library, run the following command:

.. code:: sh

  # On Linux or MacOS
  python3 -m pip install -U git+https://github.com/VarMonke/Github-Api-Wrapper
  
  # On Windows
  py -m pip install -U git+https://github.com/VarMonke/Github-Api-Wrapper
  
Quick Example
-------------
  
.. code:: py
  
  import github
  import asyncio
  
  async def main():
    client = await github.GHClient()

    user = await client.get_user(user='GithubPythonBot')

    print(user)
    print(user.html_url)

  asyncio.run(main())

.. code:: sh
  # Output
  <User login: 'GithubPythonBot', id: 104489846, created_at: 2022-04-27 07:31:26>
  https://github.com/GithubPythonBot

  
Links
-----
- `Discord Server <https://discord.gg/DWhwsQ5TsT>`_
- `GitHub API Documentation <https://docs.github.com/en/rest>`_
