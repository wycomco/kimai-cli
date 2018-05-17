clean:
	rm -rf ./dist

build: clean
	pipenv run python setup.py sdist
	openssl sha256 < dist/*
