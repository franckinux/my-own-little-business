#!/bin/sh
echo "admin password is 'admin'. For development server only !"
psql molb -c "UPDATE client SET password_hash = '\$5\$rounds=535000\$MpU6UJBRpylnIETC\$C1hdHINEXpzS4mYDoLREFx7L3SBlSB8.hmcStA1xE32' WHERE login = 'admin'"
