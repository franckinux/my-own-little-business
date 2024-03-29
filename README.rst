Packages to install
===================

Update the package list:

.. code-block:: console

    sudo apt-get update

For cryptography python module: ::

.. code-block:: console

    sudo apt install libssl-dev

For printing the sources: ::

.. code-block:: console

    sudo apt install enscript psutils

For pipdeptree Python module module:

.. code-block:: console

    sudo apt install graphviz

Python packages to install
==========================

Update your PATH environment variable (possibly in your bashrc):

.. code-block:: console

    $ export PATH=~/.local/bin:$PATH

Install molb
============

**Note**: if your user is not called `molb` as in the following instructions,
add "-U user" and "-W" options to dropdb, creatdb and psql commands.

**Note**: in order for the postgresql authentication to work, you may have to
change the authentication method from *peer* to *scram-sha-256* in PostgreSQL
`pg_hba.conf` configuration file for all users except postgres user.

Create a database user: ::

.. code-block:: console

    molb@hostname$ sudo -i -u postgres
    [sudo] Mot de passe de molb :
    postgres@hostname:~$ createuser --pwprompt --createdb molb
    Enter password for new role:
    Enter it again:
    postgres@hostname:~$ exit
    logout
    molb@hostname$

Create a virtual env, install molb and its dependencies: ::

.. code-block:: console

    $ git clone https://github.com/franckinux/my-own-little-business.git
    $ cd /path/to/my-own-little-business
    $ python3 -m venv .venv --prompt molb --upgrade-deps

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
~/.bashrc file: ::

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

Autoactivation of the python virtual environment
================================================

Create this script in your home directory (~/cd.sh):

.. code-block:: console

    function cd()
    {
        if [ -f .exit.sh ]; then
            source .exit.sh;
        fi

        if [ -z $* ]; then
            builtin cd ~
        else
            builtin cd "$*"
        fi

        if [ -f .enter.sh ]; then
            source .enter.sh;
        fi
    }

And add this line at the end of your ~/.bashrc file:

.. code-block:: console

    source ~/cd.sh

Any command present in `.enter.sh` will be execute when entering the directory
it is located in.

Any command present in `.exit.sh` will be execute when exiting the directory
it is located in.

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

- `JQuery <https://code.jquery.com/jquery/>`_ - Version 3.7.1 ;
- `Bootstrap 4 <http://getbootstrap.com/>`_ - Version 4.6.2 ;
- `Popper <https://popper.js.org/>`_ - Version 2.11.8 ;
- `Moment <https://momentjs.com/>`_ - Version 2.30.1 ;
- `Tempus Dominus - Bootstrap 4 <https://github.com/tempusdominus/bootstrap-4>`_ - Version 5.39.0 ;
- `Font Awesome <https://fontawesome.com/>`_ - Version 5.14.4 ;
- `Leaflet <https://leafletjs.com/>`_ - Version 1.9.4 ;

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
