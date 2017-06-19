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
