import requests

class Api:
	@staticmethod
	def format(response, response_seasons=None):
		store = dict()
		#process the request about show data first
		store["id"]=response["id"] if ("id" in response) else -1
		store["name"]=response["name"] if ("name" in response) else ""
		store["descr"]=response["summary"] if ("summary" in response) else ""
		store["premiered"] = response["premiered"] if ("premiered" in response and response["premiered"]!= None) else ""
		store["ended"] = response["ended"] if ("ended" in response and response["ended"] != None) else ""
		#next the data about seasons is to be checked
		if response_seasons!=None and len(response_seasons)>0:
			last_ep = response_seasons[-1]
			store["num_seasons"]=last_ep["season"] if ("season" in last_ep) else 0
			store["num_episodes"]=last_ep["number"] if ("number" in last_ep) else 0
		else:
			store["num_seasons"]=0
			store["num_episodes"]=0

		#default search tags
		if "Anime" in response["genres"]:
			store["tags"]=["anime"]
		elif response["type"]=="Animation":
			store["tags"]=["cartoon"]
		else:
			store["tags"]=["live-action"]

		return store

	
	@staticmethod
	def search(name):
		url = f"https://api.tvmaze.com/search/shows?q={name}"
		response = requests.get(url)

		series_store = []
		if response.status_code == 200:
			for data in response.json():
				series_store.append(Api.format(data["show"]))
		else:
			print(f"Bad requests 404 for show {id} :3")
			return None
		return series_store

	@staticmethod
	def get_data(id):
		# urls are formatted for the get requests
		url = f"https://api.tvmaze.com/shows/{id}"
		url_seasons = f"https://api.tvmaze.com/shows/{id}/episodes"

		response = requests.get(url)
		response_seasons = requests.get(url_seasons)
		# the error code is checked in case of a bad response
		if response.status_code == 200 and response_seasons.status_code==200:
			data = response.json()
			seasons_data = response_seasons.json()
			#data needs to be formatted in a consistent way
			store = Api.format(data, seasons_data)
			return store
		else:
			print(f"Bad requests 404 for show {id} :3")
			return None
