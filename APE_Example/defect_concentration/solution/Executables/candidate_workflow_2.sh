#!/bin/bash
if [ $# -ne 1 ]
	then
		echo "1 argument(s) expected."
		exit
fi
node81407563=$1

python - << EOF
from pyiron.project import Project
pr = Project('example_project')

structure = pr.create.structure.ase.bulk(Material, cubic=True)

# Create Vacancy Structure
vacancy_structure = structure.copy()
del vacancy_structure[1]

"Error. Tool 'calc_chemical_potential_A' is missing the execution code."
"Error. Tool 'create_antisite_Fe' is missing the execution code."
# Relax Structure
relax_job = pr.create_job(job_type=pr.job_type.Lammps, job_name='lammps_relax')
relax_job.structure = vacancy_structure
relax_job.potential = relax_job.list_potentials()[0]
relax_job.calc_minimize(pressure=0.0)
relax_job.run()
relax_structure = relax_job.get_final_structure()

"Error. Tool 'calc_chemical_potential_B' is missing the execution code."
"Error. Tool 'calculate_dfe_1AS_1Vac_AB' is missing the execution code."
"Error. Tool 'calc_defect_concentration' is missing the execution code."
echo "1. output is: $node-1569910685"