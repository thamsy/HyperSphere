import time
import pickle
import os
import os.path
import sys

import numpy as np
from torch.autograd import Variable

from HyperSphere.GP.models.gp_regression import GPRegression
from HyperSphere.GP.kernels.modules.matern52 import Matern52
from HyperSphere.GP.inference.inference import Inference
from HyperSphere.BO.acquisition_maximization import suggest
from HyperSphere.feature_map.functionals import *

from HyperSphere.test_functions.benchmarks import branin, levy

from HyperSphere.BO.bayesian_optimization_utils import model_param_init, optimization_init_points, EXPERIMENT_DIR


def cube_BO(n_eval=200, **kwargs):
	if 'path' in kwargs.keys():
		path = kwargs['path']
		if not os.path.exists(path):
			path = os.path.join(EXPERIMENT_DIR, path)
		model_filename = os.path.join(path, 'model.pt')
		data_config_filename = os.path.join(path, 'data_config.pkl')

		model = torch.load(model_filename)
		data_config_file = open(data_config_filename, 'r')
		locals().update(pickle.load(data_config_file))
		data_config_file.close()

		inference = Inference((x_input, output), model)
	else:
		n_spray = 10
		n_random = 10
		func = kwargs['func']
		if func.dim == 0:
			assert 'dim' in kwargs.keys()
			ndim = kwargs['dim']
		else:
			ndim = func.dim
		dir_list = [elm for elm in os.listdir(EXPERIMENT_DIR) if os.path.isdir(os.path.join(EXPERIMENT_DIR, elm))]
		folder_name_root = func.__name__ + '_D' + str(ndim) + '_cube'
		folder_name_suffix = [elm[len(folder_name_root):] for elm in dir_list if elm[:len(folder_name_root)] == folder_name_root]
		next_ind = 1 + np.max([int(elm) for elm in folder_name_suffix if elm.isdigit()] + [-1])
		os.makedirs(os.path.join(EXPERIMENT_DIR, folder_name_root + str(next_ind)))
		model_filename = os.path.join(EXPERIMENT_DIR, folder_name_root + str(next_ind), 'model.pkl')
		data_config_filename = os.path.join(EXPERIMENT_DIR, folder_name_root + str(next_ind), 'data_config.pkl')

		search_cube_half_sidelength = 1

		lower_bnd = -torch.ones(ndim) * search_cube_half_sidelength
		upper_bnd = torch.ones(ndim) * search_cube_half_sidelength

		x_input = Variable(torch.ger(torch.arange(0, 2), torch.ones(ndim)))
		output = Variable(torch.zeros(x_input.size(0), 1))
		for i in range(x_input.size(0)):
			output[i] = func(x_input[i])

		kernel_input_map = id_transform
		model = GPRegression(kernel=Matern52(ndim=kernel_input_map.dim_change(ndim), input_map=kernel_input_map))
		model_param_init(model, output)

		time_list = [time.time()] * 2
		elapse_list = [0, 0]

		inference = Inference((x_input, output), model)
		inference.sampling(n_sample=100, n_burnin=0, n_thin=1)

	stored_variable_names = locals().keys()
	ignored_variable_names = ['kwargs', 'data_config_file', 'dir_list', 'folder_name_root', 'folder_name_suffix',
	                          'next_ind', 'model_filename', 'data_config_filename', 'i',
	                          'kernel_input_map', 'model', 'inference']
	stored_variable_names = set(stored_variable_names).difference(set(ignored_variable_names))

	for _ in range(n_eval):
		inference = Inference((x_input, output), model)
		learned_params = inference.sampling(n_sample=10, n_burnin=0, n_thin=10)

		x0 = optimization_init_points(x_input, output, lower_bnd, upper_bnd, n_spray=n_spray, n_random=n_random)
		next_eval_point = suggest(inference, learned_params, x0=x0, reference=torch.min(output)[0], bounds=(lower_bnd, upper_bnd))

		time_list.append(time.time())
		elapse_list.append(time_list[-1] - time_list[-2])

		x_input = torch.cat([x_input, next_eval_point])
		output = torch.cat([output, func(x_input[-1])])

		rect_str = '/'.join(['%+.4f' % x_input.data[-1, i] for i in range(0, x_input.size(1))])
		time_str = time.strftime('%H:%M:%S', time.gmtime(time_list[-1])) + '(' + time.strftime('%H:%M:%S', time.gmtime(elapse_list[-1])) +')  '
		print(('\n%4d : ' % (x_input.size(0))) + time_str + rect_str + '    =>' + ('%12.6f (%12.6f)' % (output.data[-1].squeeze()[0], torch.min(output.data))))

		torch.save(model, model_filename)
		stored_variable = dict()
		for key in stored_variable_names:
			stored_variable[key] = locals()[key]
		f = open(data_config_filename, 'w')
		pickle.dump(stored_variable, f)
		f.close()


if __name__ == '__main__':
	if len(sys.argv) == 1:
		cube_BO(n_eval=200, func=levy, dim=20)
	elif len(sys.argv) == 2:
		cube_BO(n_eval=100, path=sys.argv[1])
	elif len(sys.argv) == 3:
		cube_BO(n_eval=int(sys.argv[2]), path=sys.argv[1])
