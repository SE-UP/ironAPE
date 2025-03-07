#!/bin/bash
if [ $# -ne 1 ]
	then
		echo "1 argument(s) expected."
		exit
fi
node-88251349=$1

python - << EOF
from pyiron.project import Project
pr = Project('example_project')

structure = pr.create.structure.ase.bulk(Element, cubic=True)
del structure[[1]]

job = pr.create_job(job_type=pr.job_type.Vasp, job_name='vasp_job')
job.structure = structure

murn = pr.create_job(job_type=pr.job_type.Murnaghan, job_name='murn')
murn.ref_job = job

murn.run(delete_existing_job=True)

print(pr['murn']['output/equilibrium_bulk_modulus'])
EOF

echo "1. output is: $node120152246"