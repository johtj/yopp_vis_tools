import xarray as xr
import pandas as pd
import panel as pn
import numpy as np
import datetime as dt
from functools import partial

"""This file contains the functions responsible for fetching data via Thredds using OPeNDAP 
   from the YOPP data portal hosted by MetNorway. 
"""

#creates urls for model data
def get_urls_mod(start_date,end_date,start_time,model_name,site_name,variable_list,concat_day=0):
    
    if concat_day == 2:
        start_date  = start_date-dt.timedelta(days=2) 
    elif concat_day == 1:
        start_date  = start_date-dt.timedelta(days=1)
    
    if site_name == "utqiagvik":
        site_name = "barrow"
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

#creates urls for observational data 
def get_urls_obs(site_name, ftype,sop):
    url_base = "https://thredds.met.no/thredds/dodsC/alertness/YOPP_supersite/obs/"

    if sop == "1":
        obs_url = url_base+site_name+"/"+site_name+"_obs_"+ftype+"_20180201_20180331.nc"
    elif sop == "2":
        obs_url = url_base+site_name+"/"+site_name+"_obs_"+ftype+"_20180201_20180331.nc"
    
    return obs_url

#takes one day from each file to concatenated while opening in get data
#the day selection is given to the user, used by get_data
def day_sel(xarray,concat_day):
    xarray = prep_data(xarray)
    shift = np.timedelta64((24),'h')*concat_day
    t_step = xarray['time'][1].values - xarray['time'][0].values
    start_time = xarray['time'][0].values+shift
    end_time = start_time+np.timedelta64((24),'h')-t_step
    xarray = xarray.sel(time=slice(start_time,end_time))
    return xarray

#handles discrepancies between the files.
#If there exists an extra dim(s) for latitude and longitude it is removed. 
#Same in the case using station_id for indexing of multiple points.
#used by get_data
def prep_data(xarray):
    if 'lat' in xarray.dims and 'lon' in xarray.dims:
        xarray = xarray.isel(lat=0,lon=0)
    elif 'station_id' in xarray.dims:
        xarray = xarray.isel(station_id=0)
    return xarray

#handles the reading of model or observational data from url.
#for the model case it is either in either concatenated or stacked form, the default case is stacked
#in the concatenated case a concatination day is either given in the function call
#or default set to the first day.
def get_data(out_type,urls,read_type,concat_day=0):
    
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
            ds = xr.open_dataset(urls)
        else:
            #open stacked dataset
            ds = xr.open_mfdataset(urls,concat_dim=['stime'],combine='nested',preprocess=prep_data)

    
    except ValueError:
        return xr.Dataset, "Error reading " + read_type +" data, value error occured"
    except OSError as ex:
        if ex.errno == -77:
            return xr.Dataset, "Error reading " + read_type +" data, OS error occurred, variable not in dataset."
        elif ex.errno == -90:
            return xr.Dataset, "Error reading " + read_type + " : "+ ex.args[1]
        else:
            return xr.Dataset, "Error reading " + read_type +" data, OS error occured: "+str(ex.errno)
    except Exception as ex:
        return xr.Dataset, "Error reading " + read_type +". Error: "+ex
            
    return ds, None

#handles the difference in naming for the height variables
#accounts for lack of standard in current model files
def get_height_vars(model):
    if model == 'slav-rhmc':
        variables = ["zg","Orog"] 
    elif model == 'icon-dwd':
        variables = ['hfull','orog']
    elif model == 'ECCC-CAPS':
        variables = ['zg']
    elif model in 'AROME-Arctic':
        variables = ['zg']
    else:
        variables = ['zg','zghalf']
    return variables

#handles the calculation of height variables in the different 
#model cases
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

def dims_sonde_obs(site_name):

    if site_name in ['sodankyla','tiksi','eureka']:
        height_dim = None
        time_dim = None
        return height_dim,time_dim
    elif site_name == 'utqiagvik':
        height_dim = 'hgt_sonde'
        time_dim = 'time_release_sonde'
        return height_dim,time_dim
    elif site_name == 'whitehorse' or site_name == 'iqaluit':
        height_dim = 'height_sonde'
        time_dim = 'time'
        return height_dim,time_dim
    elif site_name == 'nyalesund':
        height_dim = 'hgt_sonde'
        time_dim = 'time_nominal'
        return height_dim,time_dim
        