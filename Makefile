
clean:
	rm -rf build; rm -rf dist; rm -rf *.egg-info; rm -rf statcore/*.so;rm -rf statcore/*.c;rm -rf *.so

venv:
	virtualenv venv

install: venv
	. venv/bin/activate && pip install -e . && pip install pytest pytest-cov

test: install
	./venv/bin/pytest -s -vvv --pdb tests --cov pyestate

publish:
	rm -rf dist && python setup.py sdist bdist_wheel && \
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*