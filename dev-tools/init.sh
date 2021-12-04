file=db.sqlite3
# Control will enter here if $file exists
if [ -e "$file" ]; then
  rm $file
fi

src/vocabulary-trainer migrate
src/vocabulary-trainer shell < dev-tools/create_user.py