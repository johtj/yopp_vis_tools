import xarray as xr
import panel as pn
from thredds_crawler.crawl import Crawl
import datetime as dt
import functools as fn

#Create the widgets and set dependencies, returns a list of widgets ========================
def create_widgets():
    #widgets that are dependent on each other =================================================
    #==========================================================================================
    site_name = pn.widgets.Select(
        name="Site", options=['sodankyla','tiksi'], margin=(0, 20, 0, 0)
    )


    model_name = pn.widgets.Select(
        name="model", options=[], margin=(0, 20, 0, 0)
    )


    variable = pn.widgets.Select(
        name="Variables", options=[], margin=(0, 20, 0, 0)
    )

    #==========================================================================================
    #select SOP based on avaiable files? assume it exists for all?
    #disable SOP choices based on file availability? how easily check this?
    sop = pn.widgets.Select(
        name="SOP", options=['SOP1','SOP2'], margin=(0, 20, 0, 0)
    )

    #set dates based on selected SOP
    dates = pn.widgets.DateRangeSlider(
        name='Date Range Slider',
        start=dt.datetime(2018, 2, 2), end=dt.datetime(2018, 3, 31),
        value=(dt.datetime(2018, 2, 2), dt.datetime(2018, 3, 31))
    )

    #widgets that remain constant regardless of model selected=================================
    #==========================================================================================
    concat_day = pn.widgets.Select(
        name="Model day selected", options={1:0,2:1,3:2}, margin=(0,20,0,0)
    )

    start_time = pn.widgets.Select(
        name="Start time", options=['00','12'], margin=(0, 20, 0, 0)
    )

    site_name.link(model_name,callbacks={'value':update_models})
    site_name.value = ' '
    
   # model_name.param.watch(fn.partial(update_variables,site_name = site_name,dates = dates),['value'])
    #model_name.param.trigger('value')
    model_name.link(variable,callbacks={'value':fn.partial(update_variables,site = site_name.value,dates = dates)})
    #model_name.value = ' '

    #sop.link(dates,callbacks={'value':update_dates})
    #sop.value = ' '
    #sop.param.watch(update_dates,['value'])
    #sop.param.trigger('value')

    
    widgets = [site_name,model_name,variable,dates,sop,concat_day,start_time]

    return widgets

#Update functions for updates triggered by changes in dependant widgets =======================
def update_models(target,event):
    site  = event.new
    if site == 'sodankyla':
        models = ['AROME-Arctic','ifs-ecmwf'] #TO DO: do list models that are available for sodankyla read in from portal
        target.options = models
    elif site == 'tiksi':
        models = ['ifs-ecmwf']  #TO DO: do list models that are available for sodankyla read in from portal
        target.options = models
        
        
def update_variables(events,site,dates):
    model = events.new
    st = dates.value[0].strftime("%Y-%m-%d").replace("-","")
    base = 'https://thredds.met.no/thredds/catalog/alertness/YOPP_supersite/'
    
    url = base+model+'/'+site+'/catalog.html'
    regex = '.*'+st+'00\.nc'
    file = Crawl(url, select=[regex]).datasets[0].services[0]['url']

    ds = xr.open_dataset(file)

    ds_variables = ds.data_vars
    variables = {}
    for name, stuff in ds_variables.items():
        if len(stuff.coords.dims) == 1 and stuff.coords.dims[0] == 'time':
            #needs additional filter for wind stuff and other vars that need calculating
            variables[stuff.attrs['long_name']] = name

    variable.options = variables

def update_dates(event,target):
    sop_choice = event.new
    if sop_choice == 'SOP1':
        target.start = dt.datetime(2018, 2, 1)
        target.end = dt.datetime(2018, 3, 31)
        target.value = (dt.datetime(2018, 2, 2),dt.datetime(2018, 3, 31))
    elif sop_choice == 'SOP2':
        target.start = dt.datetime(2018, 7, 1)
        target.end = dt.datetime(2018, 9, 30)
        target.value = (dt.datetime(2018, 7, 1),dt.datetime(2018, 9, 30))
