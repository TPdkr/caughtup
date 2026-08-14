from enum import Enum
from api import Api
import json


class Status(Enum):
	HAVENT_STARTED = 0
	IN_PROGRESS = 1
	CAUGHT_UP = 2


class Series:
	keys = ["id", "name","num_seasons","num_episodes","stopped_at", 
		 "status","descr","platform","premiered","ended", "tags"]


	def __init__(self, store):
		#all key attributes are set based on provided data
		for key in self.keys:
			if key!="status" and key in store.keys():
				setattr(self, key, store[key])
			elif key=="tags":
				setattr(self, key, [])
			elif key =="num_seasons" or key=="num_episodes":
				setattr(self, key, 0)
			else:
				setattr(self, key, None)

		#for new series we need to restart the progress
		if self.stopped_at == None:
			self.stopped_at = [0,0]

		#edge case in case some data is missing for comparison
		if self.stopped_at[1]==None or self.stopped_at[1]=="null":
			self.stopped_at[1]=0
		if self.num_episodes==None or self.num_episodes=="null":
			self.num_episodes = 0
		
		#status check
		if self.stopped_at == [0,0]:
			self.status = Status.HAVENT_STARTED
		elif self.stopped_at[0] < self.num_seasons or self.stopped_at[1] < self.num_episodes:
			self.status = Status.IN_PROGRESS 
		else:
			self.status = Status.CAUGHT_UP

	def print(self):
		'''
		print the instance contents into the terminal directly
		'''
		for key in self.keys:
			print(f"{key}: {getattr(self, key)}")

	def reset(self):
		'''
		reset user progress, set stopped at to start
		'''
		self.stopped_at = (0,0)
		self.status = Status.HAVENT_STARTED

	def set_stopped_at(self,spot):
		'''
		set the point where the user stopped

		Args:
			spot: an array of season num, episode num
		'''
		self.stopped_at = [spot[0],spot[1]]
		#status check
		if self.stopped_at == [0,0]:
			self.status = Status.HAVENT_STARTED
		elif self.stopped_at.first < self.num_seasons or self.stopped_at.second < self.num_episodes:
			self.status = Status.IN_PROGRESS 
		else:
			self.status = Status.CAUGHT_UP

	def all_caught_up(self):
		'''
		set the point of stop to be latest episode
		'''
		if self.num_episodes !=None:
			self.stopped_at = [self.num_seasons, self.num_episodes]
		else:
			self.stopped_at = [self.num_seasons, 0]
		self.status = Status.CAUGHT_UP

	def add_tag(self, tag):
		'''
		add a tag to the list of tags

		Args:
			tag: tag to add
		'''
		if tag in self.tags:
			return -1
		else:
			self.tags.append(tag)
			return 0

	def remove_tag(self, tag):
		'''
		remove a tag from the list of tags

		Args:
			tag: tag to remove
		'''
		if tag not in self.tags:
			return -1
		else:
			self.tags.remove(tag)
			return 0

	def check_for_updates(self):
		'''
		update the instance info to the latest info about the series.
		set status to updated if new episode or season info appears.
		'''
		print("Checking for updates for a series using the id")
		data = Api.get_data(self.id)
		num_episodes_old=0
		num_episodes_old=0

		#read the data and update
		for key in self.keys:
			if key!="status" and key in data.keys():
				if key=="num_seasons":
					num_seasons_old = getattr(self,key)
					num_episodes_old = getattr(self,"num_episodes")
				setattr(self, key, data[key])

		#check for updates
		if num_seasons_old!=self.num_seasons or num_episodes_old!=self.num_episodes:
			print("Registered updates for the show")
			self.add_tag("updated")

		#status check
		if self.stopped_at == (0,0):
			self.status = Status.HAVENT_STARTED
		elif self.stopped_at[0] < self.num_seasons or self.stopped_at[1] < self.num_episodes:
			self.status = Status.IN_PROGRESS 
		else:
			self.status = Status.CAUGHT_UP

	def to_dict(self):
		store = dict()
		for key in self.keys:
			if key !=  "status":
				store[key]=getattr(self, key)
			else:
				store[key]=getattr(self, key).value

		return store
