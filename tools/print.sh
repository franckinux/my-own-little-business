#!/bin/bash
set -e

export TMPDIR=$(mktemp -d)

print_source () {
   MODDATE=$(date -r $1 +"%Y/%m/%d %H:%M")
   TMPFILE=$(mktemp -p $TMPDIR --suffix=.ps)
   cat $1 | iconv -c -f utf-8 -t iso-8859-1 | enscript -q -r -2 -E$2 -j --header="$1 - $MODDATE - Page \$% / \$=" -p $TMPFILE
}

export -f print_source

find . -type d \( -name static -o -name bootstrap \) -prune -o -name "*.py" -exec bash -c 'print_source "$0" python' {} \;
find . -type d \( -name static -o -name bootstrap \) -prune -o -name "*.html" -exec bash -c 'print_source "$0" html' {} \;
find . -type d \( -name static -o -name bootstrap \) -prune -o -name "*.sql" -exec bash -c 'print_source "$0" sql' {} \;
find . -type d \( -name static -o -name bootstrap \) -prune -o -name "*.sh" -exec bash -c 'print_source "$0" bash' {} \;
psmerge -osources.ps $TMPDIR/*.ps
ps2pdf sources.ps sources.pdf
rm sources.ps
rm -rf $TMPDIR
echo "Pages printed in sources.pdf"
