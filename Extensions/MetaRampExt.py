"""
Extension classes enhance TouchDesigner components with python. An
extension is accessed via ext.ExtensionClassName from any operator
within the extended component. If the extension is promoted via its
Promote Extension parameter, all its attributes with capitalized names
can be accessed externally, e.g. op('yourComp').PromotedFunction().

Help: search "Extensions" in wiki
"""

from TDStoreTools import StorageManager
import TDFunctions as TDF
import re

class MetaRampExt:
	"""
	MetaRampExt description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.keyOrderDAT = self.ownerComp.op('keyOrder')

		self.keys_page = self.ownerComp.customPages[0]

		self.position_prefix = 'Position'
		self.color_prefix = 'Color'
		self.delete_prefix = 'Delete'

	def collect_params(self, sourceOP, param_list):
		"""Collect params given in list from sourceOP."""
		return [sourceOP.par[i] for i in param_list]

	def get_num_params(self):
		"""Get number of keys by using keyOrderDAT table."""
		return self.keyOrderDAT.numRows - 1


	def get_digits(self, string_val: str):
		"""Return trailing digits from a string."""
		pattern = re.compile(r'\d+$')
		digits = pattern.search(string_val)
		if digits:
			return int(digits.group())
		else:
			return None

	
	def create_key_params(self, idx, new_position_val, enable_delete_val):
		"""Create new key parameters on key page using index and default values provided.
		"""
		# create position
		pos = self.keys_page.appendFloat(f'Position{idx}')
		pos[0].startSection = True
		pos[0].val = new_position_val
		pos[0].default = 0.5
		pos[0].clampMin = True
		pos[0].clampMax = True

		# create color
		color = self.keys_page.appendRGBA(f'Color{idx}')
		
		# initialize rgb to grey and alpha to 1.0
		for i in range(3):
			color[i].val = 0.5

		color[3].val = 1.0
		color[3].default = 1.0

		delete = self.keys_page.appendPulse(f'Delete{idx}')
		delete[0].readOnly = not enable_delete_val


	def OnAddKey(self):
		"""Creates Position, Color, and Delete params for new key. 

		Will first fill any missing values in numeric order then 
		move on to incrementing key indexes.
		"""
		new_position_name = 'Newkeyposition'
		new_position_val = self.ownerComp.par[new_position_name].val

		enable_delete_name = 'Enabledelete'
		enable_delete_val = self.ownerComp.par[enable_delete_name].val

		num_params = self.get_num_params() - 1
		position_param_digits = [self.get_digits(i.val) for i in self.keyOrderDAT.col('name')][1:]

		ideal_numbers_present = list(range(len(position_param_digits) + 1))
		ideal_numbers_present[-1] = 99

		# if number is in ideal but not in position param digits it's missing
		missing = [i for i in ideal_numbers_present if i not in position_param_digits]

		if missing:
			# could be more than one param missing, fill smallest num first
			next_idx = missing[0]
		else:
			# get max ignoring 99 and increment
			next_idx = max(ideal_numbers_present[:-1]) + 1
		
		self.create_key_params(next_idx, new_position_val, enable_delete_val)	


	def OnEnableDelete(self, par):
		"""Will toggle read only state for all Delete params except for 0 and 99."""
		key_params = self.keys_page.pars
		delete_params = [i for i in key_params if 'Delete' in i.name]
		if par.eval() == 1:
			for param in delete_params:
				if (param.name != 'Delete0') and (param.name != 'Delete99'):
					param.readOnly = False
		else:
			for param in delete_params:
				if (param.name != 'Delete0') and (param.name != 'Delete99'):
					param.readOnly = True


		
	def OnDeleteKey(self, par):
		"""Deletes a single key and corresponding params."""
		par_digits = str(self.get_digits(par.name))

		# cant delete 0 or 99
		if (par_digits != '0') and (par_digits != '99'):
			color_param_base_name = "".join([self.color_prefix, par_digits, 'r'])
			position_param_base_name = "".join([self.position_prefix, par_digits])

			param_names = []
			param_names.append(color_param_base_name)
			param_names.append(position_param_base_name)

			param_list = self.collect_params(sourceOP=self.ownerComp, param_list=param_names)
			
			par.destroy()
			for param in param_list:
				param.destroy()


	def SwitchKeyPositions(self):
		""""""
		num_params = self.get_num_params()

		# get proper order of keys according to position params (row, param_name_digit)
		position_params = [i.val for i in self.keyOrderDAT.col('name')][1:]
		position_param_digits = [self.get_digits(i.val) for i in self.keyOrderDAT.col('name')][1:]
		
		# create color and delete params using position digits
		color_params = ["".join([self.color_prefix, str(i)]) for i in position_param_digits]
		delete_params = ["".join([self.delete_prefix, str(i)]) for i in position_param_digits]

		# zip and unpack sorted list of parameters
		sorted_param_list = list(zip(position_params, color_params, delete_params))
		expanded_param_list = [element for tup in sorted_param_list for element in tup]
	
		self.keys_page.sort(*expanded_param_list)