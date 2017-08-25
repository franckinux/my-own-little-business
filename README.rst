Packages to install
===================

For creating the virtual environment : ::

    # apt install python3-venv

For cryptography python module : ::

    # apt install libssl-dev

For printing the sources : ::

   # apt install enscript
   # apt install psutils

Install molb
============

Create a database user : ::

    molb@machine$ sudo -i -u postgres
    [sudo] Mot de passe de molb :
    postgres@scarlatti:~$ createuser --pwprompt --createdb molb
    Enter password for new role:
    Enter it again:
    postgres@machine:~$ déconnexion
    molb@machine$

Create a virtual env : ::

    $ python3 -m venv /path/to/venv
    $ source /path/to/venv/bin/activate
    $ pip install --upgrade pip
    $ pip install wheel

Install molb and its requirements : ::

    $ git clone https://github.com/franckinux/my-own-little-business.git
    $ cd /path/to/my-own-little-business
    $ pip install -r requirements.txt
    $ pip install /path/to/my-own-little-business

Drop the database iif it exists : ::

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

    $ /path/to/venv/bin/gunicorn molb.main:app --bind 127.0.0.1:8080 --workers 3 --worker-class aiohttp.GunicornWebWorker


Tools
=====

They are located in the tools directory.

Compute password hash : ::

    $ password_hash.py "password_to_hash"
    > password = password_to_hash
    > password hash = $5$rounds=535000$q7pFcl1ZjQFRTcGs$snCKG7xVBiV.vPFRmqQQWUwGCjCFp.h6/9N.ejUpMrA

Copy the hash in admin-dev-password.sh or admin-prod-password.sh. As the create
script launcged above generates a new password each time, these scripts enables
to use always the same.

For formatting the sources in a unique pdf document having 2 pages per sheet :
::

    $ cd /path/to/my-own-lilttle-business/molb
    $ tools/print.sh
    > Pages printed in sources.pdf

Downloads
=========

These softwares are already present in molb, this is just a reminder on where they
have been townloaded from :

- `JQuery <https://code.jquery.com/jquery/>`_ - Version 1.12.4 ;
- `Bootstrap <http://getbootstrap.com/>`_ - Version 3.3.7 ;
- `DateTime Picker - Bootstrap <https://github.com/smalot/bootstrap-datetimepicker/>`_
