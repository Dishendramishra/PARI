#%%
from astropy.io import fits
from pprint import pprint
from copy import deepcopy

def update_header(filename):

    data = deepcopy(fits.getdata(filename))
    header = fits.Header()

    header["EXP_TYPE"]      =  "SCIENCE"
    header["UTC"]           =  "10:40:42"
    header["JD"]            =  ""
    header["HJD"]           =  ""
    header["BJD"]           =  ""
    header["SRC_NAME"]      =  "TOI1005"
    header["RA_DEC"]        =  "00 10 09.7590/+47 35 32.577"
    header["EXP_TIME"]      =  "5 SEC"
    header["OBSVR"]         =  "DISHENDRA"
    header["OBSRVTY"]       =  "MIRO"
    header["AIRMASS"]       =  2
    header["LONGITUD"]      =  ""
    header["LATITUDE"]      =  ""
    header["HEIGHT"]        =  ""
    header["HR_ANGLE"]      =  ""
    header["ALTITUDE"]      =  ""
    header["AZIMUTH"]       =  ""
    
    fits.writeto(filename,data=data,header=header,overwrite=1)

update_header("andromeda.fits")
