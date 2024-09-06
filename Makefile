test:
	uv run pytest

build: clean
	uv run pyproject-build --installer uv

clean:
	rm -rf dist

publish: build
	uv tool run twine upload -r pypi dist/*

publish-test: build
	uv tool run twine upload -r testpypi dist/*

.PHONY: test build clean publish publish-test
