from astroquery.simbad import Simbad

def get_planet_data(hd_names):

    data = []

    for name in hd_names:
        try:
            response = Simbad.query_object(name)
            ra = response.columns['RA'][0]
            dec = response.columns['DEC'][0]
            main_id = response.columns['MAIN_ID'][0]

            source = [] 
            source.extend([main_id,ra,dec])
            data.append(source)

        except Exception as e:
            print(e)
            print("Failed for: ",name)
    
    return data
    #             0    1   2  
    # data  = [ name, ra, dec]


if __name__ == "__main__":
    print(get_planet_data(["hd55575"]))

