file=db.sqlite3
# Control will enter here if $file exists
if [ -e "$file" ]; then
  rm $file
fi

lunes_cms/lunes-cms-cli migrate
lunes_cms/lunes-cms-cli shell < dev-tools/create_user.py