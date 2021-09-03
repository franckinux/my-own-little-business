Packages to install
===================

Update the package list:

.. code-block:: console

    sudo apt-get update

For python installation (see [1]_):

.. code-block:: console

    sudo apt-get install make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev \
    liblzma-dev checkinstall

For cryptography python module: ::

.. code-block:: console

    sudo apt install libssl-dev

For printing the sources: ::

.. code-block:: console

    sudo apt install enscript psutils

Python 3.9.7 installation
=========================

Download python 3.9.7 (see [3]_):

.. code-block:: console

    cd tmp
    wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz
    cd Python-3.9.7
    ./configure --prefix=/usr --enable-optimizations --enable-shared \
    --with-system-expat --with-system-ffi --with-ensurepip=yes
    make
    sudo make altinstall
    cd ..
    sudo rm -rf Python-3.9.7

Python packages to install
==========================

Update your PATH environment variable (possibly in your bashrc):

.. code-block:: console

    $ export PATH=~/.local/bin:$PATH

Install molb
============

**Note**: if your user is not called molb as in the following instructions, add
"-U user" and "-W" options to dropdb, creatdb and psql commands.

**Note**: in order for the postgresql authentication to work, you may have to
change the authentication method from *peer* to *md5* in PostgreSQL pg_hba.conf
configuration file for all users except postgres user.

Create a database user: ::

.. code-block:: console

    molb@hostname$ sudo -i -u postgres
    [sudo] Mot de passe de molb :
    postgres@hostname:~$ createuser --pwprompt --createdb molb
    Enter password for new role:
    Enter it again:
    postgres@hostname:~$ déconnexion
    molb@hostname$

Create a virtual env, install molb and its dependencies: ::

.. code-block:: console

    $ git clone https://github.com/franckinux/my-own-little-business.git
    $ cd /path/to/my-own-little-business
    $ python3 -venv --prompt molb --upgrade-deps

Activate the virtualenv: ::

.. code-block:: console

    $ source .venv/bin/activate
    $ pip install -r requirements.txt

Drop the database if it exists: ::

.. code-block:: console

    $ dropdb molb

Create the database: ::

.. code-block:: console

    $ createdb molb

Export the path to the config file in an environment variable. Put it in your
~/.bashrc file or better in a .env file in your project's directory: ::

.. code-block:: console

    $ export MOLB_CONFIG=/path/to/molb.conf

Define the keys and passwords: ::

.. code-block:: console

    $ psql molb < /path/to/create/schema.sql
    $ python3 create/create.py
    > Admin password = sa2cPKHD
    $ python3 create/secret_keys.py
    $ exit

Remove useless directory: ::

.. code-block:: console

    $ rm -rf /path/to/my-own-little-business

Launch the server: ::

.. code-block:: console

    $ gunicorn molb.main:app --bind 127.0.0.1:8080 --workers 3 --worker-class aiohttp.GunicornWebWorker


pre-commit installation
=======================

.. code-block:: console

    $ pre-commit install --install-hooks

Tools
=====

They are located in the tools directory.

Compute password hash: ::

.. code-block:: console

    $ password_hash.py "password_to_hash"
    > password = password_to_hash
    > password hash = $5$rounds=535000$q7pFcl1ZjQFRTcGs$snCKG7xVBiV.vPFRmqQQWUwGCjCFp.h6/9N.ejUpMrA

Copy the hash in admin-dev-password.sh or admin-prod-password.sh. As the
create.py script launched above generates a new admin password each time, these
scripts enable to use always the same.

For formatting the source files in a unique pdf document having 2 pages per
sheet: ::

.. code-block:: console

    $ make print_sources
    > Pages printed in sources.pdf

Downloads
=========

These softwares are stored in the static directory. This is just a reminder on
where they have been taken and what are the versions used here:

- `JQuery <https://code.jquery.com/jquery/>`_ - Version 3.5.1 ;
- `Bootstrap 4 <http://getbootstrap.com/>`_ - Version 4.5.2 ;
- `Popper <https://popper.js.org/>`_- Version 2.5.1 ;
- `Moment <https://momentjs.com/>`_- Version 2.29.0 ;
- `Tempus Dominus - Bootstrap 4 <htpp://>`_ - Version 5.1.2 ;
- `Font Awesome <https://fontawesome.com/>`_- Version 5.14.0 ;
- `Leaflet <https://leafletjs.com/>`_ - Version 1.7.1 ;

Internationalization
====================

Creation: ::

.. code-block:: console

    pybabel extract -F babel-mapping.ini -k _ -k _l --no-wrap -o locales/messages.pot .
    pybabel init -i messages.pot -d translations -l en
    pybabel init -i messages.pot -d translations -l fr
    pybabel compile -d translations

Update: ::

.. code-block:: console

    pybabel extract -F babel-mapping.ini -k _ -k _l --no-wrap -o locales/messages.pot .
    pybabel update -i messages.pot --no-wrap -d translations
    pybabel compile -d translations


.. [1] `Suggested build environment <https://github.com/pyenv/pyenv/wiki#suggested-build-environment>`_
.. [2] `How To Update All Python Packages <https://www.activestate.com/resources/quick-reads/how-to-update-all-python-packages>`_
.. [3] `How To Install Python 3.9 on Ubuntu 20.04 <https://tecadmin.net/how-to-install-python-3-9-on-ubuntu-20-04/>`_
