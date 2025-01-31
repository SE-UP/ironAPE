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

job = pr.create_job(job_type=pr.job_type.Lammps, job_name='lammps')
job.structure = structure

job.potential = job.list_potentials()[0]

job.calc_md(temperature=800, pressure=0, n_ionic_steps=10000)

job.run(delete_existing_job=True)

print(job['output/generic/temperature'])
EOF

echo "1. output is: $node533558938"