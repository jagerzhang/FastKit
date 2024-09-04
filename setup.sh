#!/bin/bash
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf >/dev/null 2>&1

test -d build && rm -r build
test -d dist && rm -r dist
test -d *.egg-info && rm -r *.egg-info

test -f .env && source .env

python3 setup.py clean
python3 setup.py sdist
# python3 setup.py install

if [ -z $repo_username -o -z $repo_password ];then
    echo "repo_username or repo_password not found, plz add in .env file."
    exit
fi

if [[ $publish -eq 1 ]];then
    twine upload dist/*.tar.gz --repository-url https://mirrors.tencent.com/repository/pypi/tencent_pypi/simple --username=$repo_username --password=$repo_password
fi

test -d build && rm -r build
test -d dist && rm -r dist
test -d *.egg-info && rm -r *.egg-info
