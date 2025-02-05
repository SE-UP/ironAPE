#!/bin/bash
if [ $# -ne 0 ]
	then
		echo "0 argument(s) expected."
		exit
fi

python - << EOF
from pyiron.project import Project
pr = Project('bulk_Al')

structure = pr.create.structure.ase.bulk('Al', cubic=True)

Create Vacancy Structure

Relax Structure

Calculate Vacancy Formation Energy
EOF

echo "1. output is: $node865023986"