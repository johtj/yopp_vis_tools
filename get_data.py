import xarray as xr
import pandas as pd
import panel as pn
import numpy as np
from thredds_crawler.crawl import Crawl
import datetime as dt
from functools import partial


def get_urls_mod(start_date,end_date,start_time,model_name,site_name,variable_list,concat_day):
    
    if concat_day == 2:
        start_date  = start_date-dt.timedelta(days=2) 
    elif concat_day == 1:
        start_date  = start_date-dt.timedelta(days=1)
   
    #generate string bases
    base = "https://thredds.met.no/thredds/dodsC/alertness/YOPP_supersite/"+model_name+"/"+site_name+"/"
    file_name_start = site_name+"_"+model_name+"_"
    file_name_end = start_time+".nc"
    
    if len(variable_list) > 1:
        variable_str = ','.join(variable_list)
    else:
        variable_str = variable_list[0]
   
    variables = "?time," + variable_str
  
    
    #generate date range
    days = ((end_date - start_date)+dt.timedelta(days=1)).days  
    datelist = pd.date_range(start_date,periods=days).to_list()
 
    #generate urls
    gen_urls = lambda date: base+file_name_start+date.strftime("%Y%m%d")+file_name_end+variables
    urls = list(map(gen_urls,datelist))
   
    return urls


def get_urls_obs(site_name, ftype,sop):
    url_base = "https://thredds.met.no/thredds/catalog/alertness/YOPP_supersite/obs/"

    url = url_base+site_name+"/catalog.html"
    regex = ".*"+ftype+"_.*"

    c = Crawl(url, select=[regex])

    if sop == "1":
        sop_start = "20180201"
    else:
        sop_start = "20180701"  
  
    obs_url = ""
    for d in c.datasets:
        for s in d.services:
            if s.get("service").lower() == "opendap" and sop_start in d.name:
                obs_url = s.get("url")
    return obs_url

#takes one day from each file to concatenated while opening in get data
#the day selection is given to the user
def day_sel(xarray,concat_day):
    xarray = prep_data(xarray)
    shift = np.timedelta64((24),'h')*concat_day
    t_step = xarray['time'][1].values - xarray['time'][0].values
    start_time = xarray['time'][0].values+shift
    end_time = start_time+np.timedelta64((24),'h')-t_step
    xarray = xarray.sel(time=slice(start_time,end_time))
    return xarray

#handles discrepancies between the files, thus far only if there exists an
#extra dim for latitude and longitude. In this case it is removed.
def prep_data(xarray):
    if 'lat' in xarray.dims and 'lon' in xarray.dims:
        xarray = xarray.isel(lat=0,lon=0)
    return xarray

#handles the reading of model data from url, in either concatenated or stacked form
#default is stacked
def get_data(out_type,urls,concat_day):
    
    try:
        if out_type == 'concatenated':
            #open concatenated dataset using preprocess passing the argument of 
            #which day should be used through partial
            ds=xr.open_mfdataset(urls,
                                  concat_dim=['time'],
                                  combine='nested',
                                  preprocess=partial(day_sel,concat_day=concat_day)
            )
        elif out_type == 'observation':
            ds = xr.open_mfdataset(urls)
        else:
            #open stacked dataset
            ds = xr.open_mfdataset(urls,concat_dim=['stime'],combine='nested',preprocess=prep_data)
      
    
    except ValueError:
        return xr.Dataset, "Error reading model data, value error occured"
    except OSError as ex:
        if ex.errno == -77:
            return xr.Dataset, "Error reading model data, OS error occurred, variable not in dataset."
        else:
            return xr.Dataset, "Error reading model data, OS error occured: "+str(ex.errno)
    except:
        return xr.Dataset, "Error reading model data."
            
    return ds, None


def get_height_vars(model):
    if model == 'slav-rhmc':
        variables = ["zg","orog"] 
    elif model == 'icon-dwd':
        variables = ['hfull','orog']
    elif model == 'ECCC-CAPS':
        variables = ['zg']
    elif model in 'AROME-Arctic':
        variables = ['zg']
    else:
        variables = ['zg','zghalf']
    return variables

def calc_model_height(model,data):
    if model == "slav-rhmc":
        data['height']=data['zg']-data['Orog'] 
    elif model == 'icon-dwd':
        data['height']=data['hfull']-data['orog']
    elif model == 'ECCC-CAPS':
        data['height'] = 10.0*data['zg']
    elif model == 'AROME-Arctic':
        data['height'] = data['zg']
    else:
        data['height'] = data['zg'] - data['zghalf'][:, -1]

    return data
