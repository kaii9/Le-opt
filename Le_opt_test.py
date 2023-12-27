from lesolver import Solver
import sys

argc=len(sys.argv)
if argc != 2:
  print(sys.argv[0] +' requires 1 command line parameter:')
  print(sys.argv[0] + ' [model_file]')
  print('')
  print('E.g.')
  print(sys.argv[0] + ' /home/`whoami`/tsp.mps')
  sys.exit(1)

def runSolver(instance):
    solver = Solver()
    solver.setOptionValue('time_limit', 10800)
    solver.setOptionValue('output_flag', True)
    solver.setOptionValue('log_to_console', True)
    solver.setOptionValue('simplex_startup_strategy', 2)

    solver.readModel(instance)
    solver.run()

if __name__ == '__main__':
    runSolver(sys.argv[1])