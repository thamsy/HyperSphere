import math
import numpy as np

import torch
from torch.nn.parameter import Parameter
from HyperSphere.GP.likelihoods.modules.likelihood import Likelihood
from HyperSphere.GP.likelihoods.functions import gaussian


class GaussianLikelihood(Likelihood):

	def __init__(self):
		super(GaussianLikelihood, self).__init__()
		self.log_noise_var = Parameter(torch.FloatTensor(1))
		self.noise_scale = 0.1

	def reset_parameters(self):
		self.log_noise_var.data.normal_(std=np.abs(np.random.standard_cauchy()) * self.noise_scale).pow_(2).log_()

	def out_of_bounds(self, vec=None):
		if vec is None:
			return (self.log_noise_var.data > math.log(100)).any()
		else:
			return (vec > math.log(1000)).any()

	def n_params(self):
		return 1

	def param_to_vec(self):
		return self.log_noise_var.data.clone()

	def vec_to_param(self, vec):
		self.log_noise_var.data = vec

	def prior(self, vec):
		return np.log(np.log(1 + 2 * (self.noise_scale / np.exp(vec)) ** 2)).sum()

	def forward(self, input):
		return gaussian.GaussianLikelihood.apply(input, self.log_noise_var)

	def __repr__(self):
		return self.__class__.__name__


if __name__ == '__main__':
	likelihood = GaussianLikelihood()
	print(list(likelihood.parameters()))