import xarray as xr
import pandas as pd
import panel as pn
import numpy as np
from thredds_crawler.crawl import Crawl
import datetime as dt
from functools import partial

#takes the specifications of what should be loaded, generates a list of the relevant urls
#then sorts that list based on the given daterange.
def get_urls(start_date,end_date,start_time,model_name,site_name,variable,concat_day):

    #format the start and end date like it appears in the file names
    sd_concat = start_date.strftime("%Y-%m-%d").replace('-','')
    ed_concat = end_date.strftime("%Y-%m-%d").replace('-','')
     
    #filter urls based on start time, and load in a list
    regex = ".*"+start_time+"\.nc"
    url = "https://thredds.met.no/thredds/catalog/alertness/YOPP_supersite/"+model_name+"/"+site_name+"/catalog.html"
    c = Crawl(url, select=[regex])
    
    bracket_urls =[]
    urls_mod = []
    
    #create add on string for the urls with variable selection
    select_vars = "?time," + variable
    
    #create the actual urls, and pick out the ones that will be the first and the last in the final list
    for d in c.datasets:
        for s in d.services:
            if s.get("service").lower() == "opendap":
                urls_mod.append(s.get("url")+select_vars)
                if sd_concat in s.get("url") or ed_concat in s.get("url"):
                    bracket_urls.append(s.get("url")+select_vars)
                    
    #sort the list to get the urls in date order
    bracket_urls.sort()
    urls_mod.sort()
    
    #identify the index of where the first url of the final list and the index of the last url
    start_index = urls_mod.index(bracket_urls[0])
    end_index = urls_mod.index(bracket_urls[1])

    #one additional file is needed to get full date range
    #because the second day is used from each file
    if concat_day == 2:
        start_index  = start_index-2 
    elif concat_day == 1:
        start_index = start_index-1
    
    
    #only use the urls that are between the dates given
    urls_mod = urls_mod[start_index:end_index+1]
    url_obs = "sodankyla_obs_2018-02-01_to_2018-03-31.nc"
    return urls_mod, url_obs

#takes one day from each file to concatenated while opening in get data
#the day selection is given to the user
def day_sel(xarray,concat_day):
    xarray = prep_data(xarray)
    shift = np.timedelta64((24),'h')*concat_day
    start_time = xarray['time'][0].values+shift
    end_time = start_time+np.timedelta64((24),'h')
    xarray = xarray.sel(time=slice(start_time,end_time))
    return xarray

#handles discrepancies between the files, thus far only if there exists an
#extra dim for latitude and longitude. In this case it is removed.
def prep_data(xarray):
    if 'lat' in xarray.dims and 'lon' in xarray.dims:
        xarray = xarray.isel(lat=0,lon=0)
    return xarray

def get_model_data(out_type,urls,concat_day):
   
    if out_type == 'concatenated':
        df=xr.open_mfdataset(urls,
                              concat_dim=['time'],
                              combine='nested',
                              preprocess=partial(day_sel,concat_day=concat_day)
        ).to_dataframe() 
    else:
        df = xr.open_mfdataset(urls,concat_dim=['stime'],combine='nested',preprocess=prep_data).to_dataframe()
        df = df.unstack()
  
    return df

def get_obs_data(url, start_date,end_date,variable):

    df = xr.open_dataset(url)[variable].to_dataframe()
    df = df[start_date:end_date]

    return df
