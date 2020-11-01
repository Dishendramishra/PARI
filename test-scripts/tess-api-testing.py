#%%
import requests
from bs4 import BeautifulSoup
import re 


r = requests.get("https://exofop.ipac.caltech.edu/tess/target.php?id=169904935")

con = r.text

soup = BeautifulSoup(con, 'html.parser')

ra = re.search("\d\d:\d\d:\d\d\.\d\d",con).group(0)        # HH:MM:SS
dec = re.search("[\+-]\d\d:\d\d:\d\d\.\d\d",con).group(0)  # HH:MM:SS

print(ra," ",dec)