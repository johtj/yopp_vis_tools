import xarray as xr
import panel as pn
from thredds_crawler.crawl import Crawl
import datetime as dt
import functools as fn
import json

def populate_vars_1D():
    file = open("site_model.json")
    site_mod_dict = json.load(file)
    
    base = "https://thredds.met.no/thredds/catalog/alertness/YOPP_supersite/"
    for site in site_mod_dict.keys():
        for model in site_mod_dict[site].keys():
            url = base+model+'/'+site+'/catalog.html'
            regex = '.*'+"0201"+'00\.nc'
            file = Crawl(url, select=[regex]).datasets[0].services[0]['url']
            ds = xr.open_dataset(file)

            variables = []
            for name, stuff in ds.data_vars.items():
                if len(stuff.coords.dims) == 1 and stuff.coords.dims[0] == 'time':
                    #needs additional filter for wind stuff and other vars that need calculating
                    variables.append(name)

            site_mod_dict[site][model] = variables
            
    return site_mod_dict


#Create the widgets and set dependencies, returns a list of widgets ========================
def create_widgets(site_mod_dict):
    
    _sites_models = {i:list(site_mod_dict[i].keys()) for i in list(site_mod_dict.keys())}
    #print(_sites_models)
    
    #widgets that are dependent on each other =================================================
    #==========================================================================================
    sites = pn.widgets.Select(
    value=list(_sites_models.keys())[0], 
    options=list(_sites_models.keys())
    )

    model = pn.widgets.Select(
    value=_sites_models[sites.value][0], 
    options=_sites_models[sites.value]
    )

    variable = pn.widgets.Select(
        value=site_mod_dict[sites.value][model.value][0],
    options=site_mod_dict[sites.value][model.value]
    )

    @pn.depends(sites.param.value, watch=True)
    def _update_countries(sites):
        models = _sites_models[sites]
        model.options = models
        model.value = models[0]

    #@pn.depends(sites.param.value, watch=True)
    @pn.depends(sites.param.value,model.param.value, watch=True)
    def _update_var(sites,model):
        variables = site_mod_dict[sites][model]
        variable.options = variables
        variable.value = variables[0]

    #==========================================================================================
    #select SOP based on avaiable files? assume it exists for all?
    #disable SOP choices based on file availability? how easily check this?
    #sop = pn.widgets.Select(
    #    name="SOP", options=['SOP1','SOP2'], margin=(0, 20, 0, 0)
    #)

    #set dates based on selected SOP
    dates = pn.widgets.DateRangeSlider(
        name='Date Range Slider',
        start=dt.datetime(2018, 2, 2), end=dt.datetime(2018, 3, 31),
        value=(dt.datetime(2018, 2, 2), dt.datetime(2018, 2, 4))
    )

    #widgets that remain constant regardless of model selected=================================
    #==========================================================================================
    concat_day = pn.widgets.Select(
        name="Model day selected", options={1:0,2:1,3:2}, margin=(0,20,0,0)
    )

    start_time = pn.widgets.Select(
        name="Start time", options=['00','12'], margin=(0, 20, 0, 0)
    )
    

    
    widgets = [sites,model,variable,dates,concat_day,start_time]

    return widgets

