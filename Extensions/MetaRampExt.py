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
		self.ownerComp = ownerComp

		self.keys_page = self.ownerComp.customPages[0]

		self.position_prefix = 'Position'
		self.color_prefix = 'Color'
		self.delete_prefix = 'Delete'

	def sort_keys_enabled(self):
		"""Check if Sort keys parameter is enabled or not."""
		return bool(self.ownerComp.par.Sortkeys.eval())

	def collect_params(self, sourceOP, param_list):
		"""Collect params given in list from sourceOP."""
		return [sourceOP.par[i] for i in param_list]

	def get_position_params(self):
		"""Collect position parameters."""
		return self.ownerComp.pars(f'{self.position_prefix}*')

	def get_num_params(self):
		"""Get number of keys by using keyOrderDAT table."""
		return len(self.get_position_params())

	def get_position_param_digits(self):
		"""Collect list of position parameter digits."""
		position_params = self.get_position_params()
		return [tdu.digits(i.name) for i in position_params]
	
	def create_key_params(self, idx, new_position_val, enable_delete_val):
		"""Create new key parameters on key page using index and default values provided."""
		# create position
		pos = self.keys_page.appendFloat(f'{self.position_prefix}{idx}')
		pos[0].startSection = True
		pos[0].val = new_position_val
		pos[0].default = 0.5
		pos[0].clampMin = True
		pos[0].clampMax = True

		# create color
		color = self.keys_page.appendRGBA(f'{self.color_prefix}{idx}')
		
		# initialize rgb to grey and alpha to 1.0
		for i in range(3):
			color[i].val = 0.5

		color[3].val = 1.0
		color[3].default = 1.0

		delete = self.keys_page.appendPulse(f'{self.delete_prefix}{idx}')

		# if Enabledelete parameter True then read only should be false and vice versa
		delete[0].readOnly = not enable_delete_val

	def CollectColorKeys(self):
		"""Loop over color parameters and return rows that will represent ramp keys in script DAT."""
		rows = []
		header = ['pos', 'r', 'g', 'b', 'a']
		rows.append(header)

		# loop through each position par and build a list of position, r, g, b, a values
		for param in self.get_position_params():

			pos = param.eval()
			
			# because position and color pars share a digit we can rely on this order
			# when buidling our our color keys
			par_digit = tdu.digits(param.name)
			red = parent.META_RAMP.par[f'{self.color_prefix}{par_digit}r']
			green = parent.META_RAMP.par[f'{self.color_prefix}{par_digit}g']
			blue = parent.META_RAMP.par[f'{self.color_prefix}{par_digit}b']
			alpha = parent.META_RAMP.par[f'{self.color_prefix}{par_digit}a']

			rows.append([pos, red, green, blue, alpha])
		return rows

	def OnAddKey(self):
		"""Creates Position, Color, and Delete params for new key. 

		Will first fill any missing values in numeric order then 
		move on to incrementing key indexes.
		"""
		new_position_name = 'Newkeyposition'
		new_position_val = self.ownerComp.par[new_position_name].eval()

		enable_delete_name = 'Enabledelete'
		enable_delete_val = self.ownerComp.par[enable_delete_name].eval()

		num_params = self.get_num_params() - 1
		position_param_digits = self.get_position_param_digits()

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
		self.SwitchKeyPositions()

	def OnEnableDelete(self, par):
		"""Will toggle read only state for all Delete params except for 0 and 99."""
		key_params = self.keys_page.pars
		delete_params = [i for i in key_params if self.delete_prefix in i.name]
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
		par_digits = str(tdu.digits(par.name))

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
		"""Switch key positions if Sortkeys parameter is enabled."""
		if self.sort_keys_enabled():
			num_params = self.get_num_params()

			# collect position parameter names and values
			position_info = [(i.eval(), i.name) for i in self.get_position_params()]

			# sort by first element of tuple (position values)
			sorted_pos_info = sorted(position_info)

			position_param_names = [name for val, name in sorted_pos_info]
			position_param_digits = [tdu.digits(name) for val, name in sorted_pos_info]

			# create color and delete params using position digits
			color_param_names = ["".join([self.color_prefix, str(i)]) for i in position_param_digits]
			delete_param_names = ["".join([self.delete_prefix, str(i)]) for i in position_param_digits]

			# zip and unpack sorted list of parameters
			zipped_param_list = list(zip(position_param_names, color_param_names, delete_param_names))
			expanded_param_list = [element for tup in zipped_param_list for element in tup]

			#print(expanded_param_list)
			
			self.keys_page.sort(*expanded_param_list)