
Molecule venv requirements can
be upgraded and then
regenerated using:

sudo pip3 install --upgrade pip
sudo pip3 install --upgrade pip-tools

use ev. --resolver=backtracking for below

rm requirements-dev.txt
rm requirements.txt

pip-compile --output-file=requirements.txt requirements.in

pip-compile --output-file=requirements-dev.txt requirements-dev.in



