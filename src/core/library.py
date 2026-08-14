import json
from series import Series

class Library:
	'''
	Library class that stores all series and user data in 1 big object.
	'''
	def __init__(self,path=""):
		self.path = path
		self.series =[]

		if path!="":
			code = self.load()
			if code == -1:
				raise FileNotFoundError("file not found, error reading file")


	def load(self):
		'''
		load the series data from specified file
		'''
		try:
			with open(self.path, "r") as file:
				data = json.load(file)
				for serie in data["series"]:
					self.series.append(Series(serie))
				return 0
		except FileNotFoundError:
			print(f"Error: '{self.path}' file was not found.")
			return -1

	def save(self):
		'''
		save the series data to the specified file
		'''

		if self.path == "":
			print(f"path not specidied")
			return -1
		try:
			with open(self.path, "w") as file:
				#the data is converted to dict
				data = dict()
				data["series"]=[]
				for serie in self.series:
					data["series"].append(serie.to_dict())

				#the json string is generated
				json_str=json.dumps(data, indent=4)

				#write to file
				file.write(json_str)
				return 0
		except FileNotFoundError:
			print(f"Error: '{self.path}' file not found.")
			return -1

	def set_path(self, path):
		'''
		set the path to save data to new value

		Args:
			path: str
		'''
		self.path=path

	def check_for_updates_all(self, id_list=[]):
		'''
		check all series stored for updates
		'''
		check_id= len(id_list)!=0
		for serie in self.series:
			if not check_id or (check_id and serie.id in id_list):
				serie.check_for_updates()

	def all_caught_up_all(self,id_list=[]):
		'''
		mark all series as caught up
		'''
		check_id= len(id_list)!=0
		for serie in self.series:
			if (check_id and serie.id in id_list) or not check_id:
				serie.all_caught_up()

	def reset_all(self, id_list=[]):
		'''
		reset all series watch data to the start
		'''
		check_id= len(id_list)!=0
		for serie in self.series:
			if (check_id and serie.id in id_list) or not check_id:
				serie.reset()

	def clear_updated(self):
		'''
		remove updated status from all series that are listed as such
		'''
		for serie in self.series:
			serie.remove_tag("updated")

	def add_series(self, serie):
		'''
		add a series
		'''
		self.series.append(serie)
		serie.check_for_updates()

	def remove_series(self, serie_id):
		'''
		remove a series
		'''
		self.series = [serie for serie in self.series if serie.id!=serie_id]

	def get_tags(self):
		'''
		get a list of tags that are used
		'''
		all_tags = []
		[all_tags.extend(serie.tags)  for serie in self.series]
		return list(set(all_tags))

	def get_with(self, key_word="", tag=None, updated=False, status_id=-1):
		"""
		get series with certain filters listed below:

		Args:
			key_word: [""] search term in the name
			tag: [None] tag to look for
			updated: [False] is it updated
			status_id: [-1] status to look for
		"""
		matches = []
		for serie in self.series:
			matches_keyword = key_word == "" or key_word in serie.name
			matches_tag = tag is None or tag in serie.tags
			matches_updated = updated is False or updated is None or "updated" in serie.tags
			matches_status = status_id==-1 or serie.status.value == status_id

			if matches_keyword and matches_tag and matches_updated and matches_status:
				matches.append(serie)

		return matches
