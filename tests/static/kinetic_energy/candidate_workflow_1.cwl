cwlVersion: v1.2
class: Workflow

inputs:
  input_1: Any
  input_2: Any
  input_3: Any

steps:
  get_speed_01:
    run: get_speed.cwl
    in:
      get_speed_in_1: input_1
      get_speed_in_2: input_2
    out: [get_speed_out_1]
  get_kinetic_energy_02:
    run: get_kinetic_energy.cwl
    in:
      get_kinetic_energy_in_1: input_3
      get_kinetic_energy_in_2: get_speed_01/get_speed_out_1
    out: [get_kinetic_energy_out_1]

outputs:
  output_1:
    type: Any
    outputSource: get_kinetic_energy_02/get_kinetic_energy_out_1
