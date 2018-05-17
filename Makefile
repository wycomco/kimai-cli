clean:
	rm -rf ./dist

build: clean
	pipenv run python setup.py sdist
