clean:
	rm -rf ./dist

checksum:
	bash -c "openssl sha256 < dist/*"

build: clean
	pipenv run python setup.py sdist

dist: clean build checksum
