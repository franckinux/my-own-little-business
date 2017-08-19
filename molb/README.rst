How to use
==========

Create a user and a database : ::

    franck@machine$ sudo -i -u postgres
    [sudo] Mot de passe de franck :
    postgres@scarlatti:~$ createuser --pwprompt --createdb franck
    Enter password for new role:
    Enter it again:
    postgres@machine:~$ déconnexion
    franck@machine$

Create a virtual env : ::

    $ make venv

Use the virtual env : ::

    $ source venv/bin/activate

Install the Python packages : ::

    $ make requirements

Install the database and secret keys : ::

    $ make create

Run the server : ::

    $ make serve

Unuse the virtual env : ::

    (venv) deactivate
    $

Launching the application in production
=======================================

/path/my-own-little-business/venv/bin/gunicorn main:app --bind 127.0.0.1:8080 --workers 3 --worker-class aiohttp.GunicornWebWorker

Downloads
=========

- `JQuery <https://code.jquery.com/jquery/>`_ - Version 1.12.4 ;
- `Bootstrap <http://getbootstrap.com/>`_ - Version 3.3.7 ;
- `DateTime Picker - Bootstrap <https://github.com/smalot/bootstrap-datetimepicker/>`_

Necessary packages
==================

For creating the virtual environment : ::

    # apt install python3-venv

For cryptography : ::

    # apt install libssl-dev
