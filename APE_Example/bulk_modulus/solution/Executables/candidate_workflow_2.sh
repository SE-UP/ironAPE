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

job = pr.create_job(job_type=pr.job_type.Vasp, job_name='vasp_job')
job.structure = structure

murn = pr.create_job(job_type=pr.job_type.Murnaghan, job_name='murn')
murn.ref_job = job

murn.run(delete_existing_job=True)

print(pr['murn']['output/equilibrium_bulk_modulus'])
EOF

echo "1. output is: $node120152246"