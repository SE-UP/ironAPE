#!/bin/bash
if [ $# -ne 1 ]
	then
		echo "1 argument(s) expected."
		exit
fi
node1355219665=$1

python - << EOF
from pyiron.project import Project
pr = Project('example_project')

structure = pr.create.structure.ase.bulk(Element, cubic=True)

# Relax Structure
relax_job = pr.create_job(job_type=pr.job_type.Lammps, job_name='lammps_relax')
relax_job.structure = vacancy_structure
relax_job.potential = relax_job.list_potentials()[0]
relax_job.calc_minimize(pressure=0.0)
relax_job.run()
relax_structure = relax_job.get_final_structure()

# Create Vacancy Structure
vacancy_structure = structure.copy()
del vacancy_structure[1]

# Calculate Vacancy Formation Energy
bulk_job = pr.create_job(job_type=pr.job_type.Lammps, job_name='lammps_bulk', delete_existing_job=True)
bulk_job.structure = structure
bulk_job.potential = bulk_job.list_potentials()[0]
bulk_job.run()
E_v = relax_job.output.energy_pot[-1]
E_b = bulk_job.output.energy_pot[-1]
E_vf = E_v - (3/4 * E_b)
print(E_vf)
EOF

echo "1. output is: $node-1927115303"