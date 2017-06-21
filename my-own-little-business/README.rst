Create a virtual env : ::

    $ virtualenv --python=/usr/bin/python3.5 venv

Use the virtual env : ::

    $ source venv/bin/activate

Install the Python packages : ::

    (venv) $ pip install -r requirements.txt

Unuse the virtual env : ::

    (venv) deactivate
    $

Create a user and a database : ::

    franck@machine$ sudo -i -u postgres
    [sudo] Mot de passe de franck :
    postgres@scarlatti:~$ createuser --pwprompt --createdb franck
    Enter password for new role:
    Enter it again:
    postgres@machine:~$ déconnexion
    dranck@machine$ createdb molb

    (venv) franck@machine$ psql molb
    psql (9.5.7)
    Type "help" for help.

    molb=> \q
