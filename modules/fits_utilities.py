
#%%
from astropy.io import fits
import os
from pprint import pprint

def update_header(filename,values_dict): 
  data, header = fits.getdata(filename, header=True)
  for key in values_dict:
    header[key] = values_dict[key]
  fits.writeto(filename, data, header, overwrite=True)

  # print("Object Altitude: ", obj_altz.alt*u.deg)
  # print("Object Airmass : ", airmass)