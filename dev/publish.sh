#!/bin/bash
python setup.py bdist_wheel
python setup.py sdist
twine upload --repository pypi dist/*