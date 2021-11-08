Git configuration
=================

Name and email:

.. code-block:: console

    git config --global user.name "MY Name"
    git config --global user.email my.name@evbox.com

Aliases:

.. code-block:: console

    git config --global alias.co checkout
    git config --global alias.br branch
    git config --global alias.ci commit
    git config --global alias.st status

Credentials:

.. code-block:: console

    git config credential.helper 'cache --timeout=86400'

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
    liblzma-dev

For cryptography python module: ::

.. code-block:: console

    sudo apt install libssl-dev

For printing the sources: ::

.. code-block:: console

    sudo apt install enscript psutils

For pipdeptree Python module module:

.. code-block:: console

    sudo apt install graphviz

Python 3.9.7 installation
=========================

- Download and install python 3.9.7 (see [3]_):

.. code-block:: console

    sudo mkdir /opt/python3.9
    cd tmp
    wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz
    tar xzf Python-3.9.7.tgz
    cd Python-3.9.7
    ./configure --prefix=/opt/python3.9 --enable-optimizations --enable-shared \
    --with-system-expat --with-system-ffi --with-ensurepip=install
    make
    sudo make install
    cd ..
    sudo rm -rf Python-3.9.7

- Update the library search path:

  Create the /etc/ld.so.conf.d/python3.9.conf file containing this line:

.. code-block:: console

  /opt/python3.9/lib

 and run this command:

.. code-block:: console

    sudo ldconfig

- Update the environment variable PATH. Add this line to your ~/.profile
  file:

.. code-block:: console

    if [ -d "/opt/python3.9/bin" ] ; then
        PATH="/opt/python3.9/bin:$PATH"
    fi

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
    $ /opt/python3.9/bin/python3 -m venv .venv --prompt molb --upgrade-deps

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

Create this script in your home directory (autoactivate_venv.sh):

.. code-block:: console

    # auto activate virtualenv
    # Modified solution based on https://stackoverflow.com/questions/45216663/how-to-automatically-activate-virtualenvs-when-cding-into-a-directory/56309561#56309561
    function cd() {
      builtin cd "$@"

      ## Default path to virtualenv in your projects
      DEFAULT_ENV_PATH="./.venv"

      ## If env folder is found then activate the vitualenv
      function activate_venv() {
        if [[ -f "${DEFAULT_ENV_PATH}/bin/activate" ]] ; then
          source "${DEFAULT_ENV_PATH}/bin/activate"
          echo "Activating ${VIRTUAL_ENV}"
        fi
      }

      if [[ -z "$VIRTUAL_ENV" ]] ; then
        activate_venv
      else
        ## check the current folder belong to earlier VIRTUAL_ENV folder
        # if yes then do nothing
        # else deactivate then run a new env folder check
        parentdir="$(dirname ${VIRTUAL_ENV})"
        if [[ "$PWD"/ != "$parentdir"/* ]] ; then
          echo "Deactivating ${VIRTUAL_ENV}"
          deactivate
          activate_venv
        fi
      fi
    }

And add this line at the end of your ~/.bashrc file:

.. code-block:: console

    source ~/autoactivate_venv.sh

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
- `Popper <https://popper.js.org/>`_ - Version 2.5.1 ;
- `Moment <https://momentjs.com/>`_ - Version 2.29.0 ;
- `Tempus Dominus - Bootstrap 4 <https://github.com/tempusdominus/bootstrap-4>`_ - Version 5.1.2 ;
- `Font Awesome <https://fontawesome.com/>`_ - Version 5.14.0 ;
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
