

import pandas as pd
import os
import requests
import json
from tqdm import tqdm
import time

dirname = os.path.dirname(__file__)


api_key = "RGAPI-26afc807-7c94-4fa2-9120-56657ca8abb5"
nb_pages = 10

region = "euw1"
ranks = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND"]
divs = ["IV", "III", "II", "I"]


class API():
    def __init__(self,api_key):
        self.api_key = api_key
        try:
            os.chdir(os.path.dirname(__file__))
        except NameError:
            pass
        
    def get_from_api(self,url, api_key_given = False):
        x = None
        while x == None or x.status_code == 429 or x.status_code == 503 or x.status_code == 403:
            if api_key_given:
                x = requests.get(url)
            else:
                x= requests.get(url + self.api_key)
            if  x.status_code == 429 or x.status_code == 503:
                time.sleep(1)
            if x.status_code == 403:
                print(x.content)
                print(url + self.api_key)
                print("Time to refresh the key")
                self.api_key = input("")
        if x.status_code != 200:
            raise Exception("Error request got bad status code " + str(x.status_code) + " with message " + str(x.content) + "from url " + x.url)
        y = json.loads(x.content)
        return y
    
    def get_match_infos(self, match_id, region_alias):
        dic = {}
        url = "https://" + region_alias + ".api.riotgames.com/lol/match/v5/matches/" +match_id + "?api_key="
        y = self.get_from_api(url)
        participants = y["info"]["participants"]
        try :
            dic["win"] = participants[0]["win"]
        except:
            raise Exception()
        for p in range(len(participants)):
            dic["summonerId_"+str(p)] = participants[p]["summonerId"]
            dic["champ_" + str(p)] = participants[p]["championId"]
        return dic
        
    
    def get_match_ids(self, puuids, region_alias, games_by_player = 5, queue = 420, verbose = False):
        match_ids = []
        for puuid in tqdm(puuids, smoothing=0, disable = not verbose):
            url = "https://" + region_alias + ".api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids?queue=" + str(queue) + "&start=0&count=" + str(games_by_player) + "&api_key="
            y = self.get_from_api(url)
            match_ids += y
        return match_ids
            
    def get_mastery(self, summoner_id, champion_id, region):
        url = "https://" + region + ".api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/"+ summoner_id + "/by-champion/" +str(champion_id) + "?api_key="
        y = self.get_from_api(url)
        return y["championPoints"]
    
    def add_puuids(self, df, region, verbose = False):
        puuids = []
        for i in tqdm(range(len(df)), smoothing=0, disable = not verbose):
            y = self.get_from_api("https://"+region+".api.riotgames.com/lol/summoner/v4/summoners/"+ df.loc[i, "summonerId"] + "?api_key=")
            puuids.append(y["puuid"])
        df["puuid"] = puuids
        return df
    
    def get_summoner_ids(self, ranks, divs, region, nb_pages = 1, verbose = False):
        pages = range(1,nb_pages+1)[::-1]
        dfs = []
        for rank in ranks:
            if verbose: 
                print("Currently fetchin rank :", rank)
            for div in tqdm(divs, smoothing=0, disable = not verbose):
                temp_dfs = []
                for page in pages:
                    j = self.get_from_api("https://"+ region +".api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/" + rank + "/" + div + "?page="+ str(page) + "&api_key=")
                    df = pd.DataFrame(j)
                    temp_dfs.append(df)
                final_df = pd.concat(temp_dfs, axis = 0)
                final_df.to_csv("../data/matches/matches_data_"+ rank +"_"+div+".csv", index  = False)
                dfs.append(final_df)
        return dfs
    
verbose = True
region = "euw1"
region_alias = "europe"
api = API(api_key)
for i in range(len(ranks)):
    if verbose: 
        print("Gathering random summoner ids")
    dfs = api.get_summoner_ids([ranks[i]], divs, region, nb_pages = 5, verbose = verbose)
    rank_df = pd.concat(dfs, axis = 0).reset_index(drop = True)
    if verbose:
        print("Gathering puuids")
    rank_df = api.add_puuids(rank_df, region, verbose = verbose)
    if verbose:
        print("Gathering match ids")
    match_ids = api.get_match_ids(rank_df["puuid"], region_alias, verbose = verbose)
    L = []
    if verbose:
        print("Gathering summoners ids and champions")
    for j in tqdm(range(len(match_ids)), smoothing=0, disable = not verbose):
        try:
            L.append(api.get_match_infos(match_ids[j], region_alias))
        except:
            continue
    final_df = pd.DataFrame(L)
    
    if verbose:
        print("Gathering champion points")
    champion_points = [[] for i in range(10)]
    for j in tqdm(range(len(final_df)), smoothing=0, disable = not verbose):
        champion_points = []
        for l in range(10):
            cpoint = api.get_mastery(final_df["summonerId_"+str(l)][j], final_df["champ_"+str(l)][j], region)
            champion_points.append(cpoint)
        for l in range(10):
            final_df["championPoints_"+str(l)] = champion_points[l]
    final_df.to_csv("../data/data_points_" + ranks[i] + ".csv", index = False)