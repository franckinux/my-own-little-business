#!/bin/sh
echo "admin password is 'admin'. For development server only !"
psql molb -c "UPDATE client SET password_hash = '\$5\$rounds=535000\$pPutLyvg2MO80qCN\$P25gVRSBnwZuIl0xa3VE6lwxdkxn6mwyUrPeL9SLW96' WHERE login = 'admin'"
