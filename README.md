# DINO2

Object-relational model using sqlalchemy for DINO version 2.1 data.  
Developed and tested with/for python 3.7 and sqlite.

## Setup
Install requirements into a new virtual environment: `pipenv install`  
Install package: `python setup.py install`

## Tools

### Import data
`pipenv run python -m DINO2.tools.imp ../dino 9`

### Create graph from db and model
`pipenv run python -m DINO2.tools.graph ./docs/DINO2/model`

### Generate documentation
(use `pipenv install --dev`)

`pipenv run pdoc3 -c show_type_annotations=True -c sort_identifiers=False --html DINO2 -o ./docs --force`

`pipenv run pdoc3 -c show_type_annotations=True -c sort_identifiers=False --pdf DINO2 | iconv -f cp1252 -t utf-8 | pandoc --metadata=title:"DINO2 documentation" --toc --toc-depth=4 --from=markdown+abbreviations --pdf-engine=xelatex --variable=mainfont:"DejaVu Sans" --output=docs/docs.pdf`

## Test
`pipenv run python -m pytest` (uses test data inside <./tests/data/>)
