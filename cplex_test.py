#!/usr/bin/env python3

import docplex.mp.model as cpx
from docplex.mp.model_reader import ModelReader


import sys

argc = len(sys.argv)

if argc != 2:
 print(sys.argv[0] +' requires 1 command line parameter:')
 print(sys.argv[0] + ' [date]')
 print('')
 print('E.g.')
 print(sys.argv[0] + ' 2023-12-06')
 sys.exit(1)

filename = sys.argv[1]

# 读文件
full_path=filename

model = ModelReader.read_model(full_path,model_name='docplex_foo',solver_agent='docloud',output_level=100)

model.solve(log_output=True)
print("objective value = " + str(model.objective_value))
print(model.solve_details)
print("solve time =",model.solve_details.time)