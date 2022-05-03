Github API Wrapper
==================

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

**Python 3.8 or higher**

To install the library, run the following command

.. code:: sh

  #Linux/macOS
  python3 -m pip install -U git+https://github.com/VarMonke/Github-Api-Wrapper
  
  #Windows
  py -m pip install -U git+https://github.com/VarMonke/Github-Api-Wrapper
  
Quick Example
-------------
  
.. code:: py
  
  import github
  import asyncio
  
  async def main():
    client = await github.GHClient()
    return await client.get_user(user='GithubPythonBot')

  user = asyncio.run(main())
  print(user)
  print(user.html_url)

.. code:: sh
  #Output
  <User login: 'GithubPythonBot', id: 104489846, created_at: 2022-04-27 07:31:26>
  https://github.com/GithubPythonBot

  
Links
-----
`Discord Server <https://discord.gg/DWhwsQ5TsT>`_