Your personal config files will be named (with a '~' instead '-' after "business") :

my-own-little-business~something.ini

The reference config file is named :

my-own-little-business-dev.ini

Setup symbolic link to the real ini file :

$ ln -s my-own-little-business-dev.ini my-own-little-business.ini
or
$ ln -s my-own-little-business~something.ini my-own-little-business.ini

This enables you to have a reference config file in git that never embed your secret informations.
Your personal configuration files as long as the symbolic link are ignored by git.
