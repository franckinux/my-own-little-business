Packages to install
===================

For cryptography python module : ::

    # apt install libssl-dev

For printing the sources : ::

    # apt install enscript
    # apt install psutils

Install pipenv in user environment : ::

    $ python3 -m pip install pipenv

and update your PATH environment variable (possibly in your bashrc) :

    $ export PATH=~/.local/bin:$PATH

Install molb
============

**Note** : if your user is not called molb as in the following instructions, add
"-U user" and "-W" options to dropdb, creatdb and psql commands.

**Note** : in order for the postgresql authentication to work, you may have to
change the authentication method from *peer* to *md5* in PostgreSQL pg_hba.conf
configuration file for all users except postgres user.

Create a user database : ::

    molb@machine$ sudo -i -u postgres
    [sudo] Mot de passe de molb :
    postgres@scarlatti:~$ createuser --pwprompt --createdb molb
    Enter password for new role:
    Enter it again:
    postgres@machine:~$ déconnexion
    molb@machine$

Create a virtual env, install molb and its dependencies : ::

    $ git clone https://github.com/franckinux/my-own-little-business.git
    $ cd /path/to/my-own-little-business
    $ pipenv install
    $ pipenv update
    $ pipenv install -e .

Drop the database if it exists : ::

    $ dropdb molb

Create the database : ::

    $ createdb molb

Export the path to the config file in an environment variable : ::

    $ export MOLB_CONFIG=/path/to/molb.conf

Define the keys and passwords : ::

    $ psql molb < /path/to/create/schema.sql
    $ python3 create/create.py
    > Admin password = sa2cPKHD
    $ python3 create/secret_keys.py

Remove useless directory : ::

    $ rm -rf /path/to/my-own-little-business

Launch the server : ::

    $ gunicorn molb.main:app --bind 127.0.0.1:8080 --workers 3 --worker-class aiohttp.GunicornWebWorker


Tools
=====

They are located in the tools directory.

Compute password hash : ::

    $ password_hash.py "password_to_hash"
    > password = password_to_hash
    > password hash = $5$rounds=535000$q7pFcl1ZjQFRTcGs$snCKG7xVBiV.vPFRmqQQWUwGCjCFp.h6/9N.ejUpMrA

Copy the hash in admin-dev-password.sh or admin-prod-password.sh. As the
create.py script launched above generates a new admin password each time, these
scripts enable to use always the same.

For formatting the source files in a unique pdf document having 2 pages per
sheet : ::

    $ make print_sources
    > Pages printed in sources.pdf

Downloads
=========

These softwares are already present in molb, this is just a reminder on where they
have been downloaded from :

- `JQuery <https://code.jquery.com/jquery/>`_ - Version 1.12.4 ;
- `Bootstrap <http://getbootstrap.com/>`_ - Version 3.3.7 ;
- `DateTime Picker - Bootstrap <https://github.com/smalot/bootstrap-datetimepicker/>`_
