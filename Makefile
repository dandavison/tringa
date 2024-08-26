build: clean
	uv run pyproject-build --installer uv

clean:
	rm -rf dist

publish:
	uv tool run twine upload -r pypi dist/*

publish-test:
	uv tool run twine upload -r testpypi dist/*

.PHONY: build clean publish publish-test
