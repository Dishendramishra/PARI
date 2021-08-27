
#%%
from astropy.io import fits
import os
from pprint import pprint

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from datetime import datetime

def update_header(filename,values_dict): 
  data, header = fits.getdata(filename, header=True)
  for key in values_dict:
    header[key] = values_dict[key]
  fits.writeto(filename, data, header, overwrite=True)

def get_airmass(obj_str):

  Gurushikar = {"Latitude" : 24.6531*u.deg, "Longitude": -72.7794*u.deg, "Altitude" : 1765*u.m}

  obj = SkyCoord.from_name(obj_str)
  
  # bear_mountain = EarthLocation(lat=41.3*u.deg, lon=-74*u.deg, height=390*u.m)
  bear_mountain = EarthLocation(lat=Gurushikar["Latitude"],
                                lon=Gurushikar["Longitude"],
                                height=Gurushikar["Altitude"],
  )
  utcoffset = -4*u.hour
  time = Time(datetime.utcnow()) - utcoffset
  obj_altz = obj.transform_to(AltAz(obstime=time,location=bear_mountain))
  airmass = obj_altz.secz
  # print("Object Altitude: ", obj_altz.alt*u.deg)
  # print("Object Airmass : ", airmass)