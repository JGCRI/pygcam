"""Functions for processing water usage from power plant location data."""

import json
import csv


def pplnt_grid(tuple_list, grid_size = [720, 360], extent= [-180, -90, 180, 90]):
    """Converts (longitude, latitude, water-usage) tuples to dictionary.

    Maps (longitude, latitude, water-usage) tuples to a grid. Each(lon,lat) value
    is converted to an (i,j) value representing a column and row of the grid.
    Outputs a dictionary with keys that are (i,j) pairs and values that are
    the sum of water usage withiin each grid cell (i,j). 

    Arguments:
        tuple_list - list of (lon, lat, water-usage) tuples
         grid_size - size of the grid; [ncols, nrows].
            extent - list of (lon,lat) coordinates of the grid edges.
                        extent[0] and  extent[1] are (lon,lat) coordinates of
                        lower left corner of grid. extent[2] and extent[3] are
                        (lon,lat) coordinates of upper right corner of grid.

    Return value: a dictionary, with keys of (i,j) coordinates. Each (i,j) pair
                    contains a value that is the sum of all water usage values
                    for power plants within that grid cell. 
        
    """

    #Initialize grid dictionary
    grid = {}
    
    #Map (lon,lat) dimensions to (i,j) dimensions
    lon_start = extent[0] 
    lat_start = extent[1]
    lon_end = extent[2]
    lat_end = extent[3]

    i_start = 0 
    j_start = 0
    i_end = grid_size[0] 
    j_end = grid_size[1] 
    
    lon_offset = abs(lon_start - i_start)
    lat_offset = abs(lat_start - j_start)
    
    #Get dimensions of individual cells
    lon_len = abs(lon_end - lon_start) #lat, lon dimensions of grid
    lat_len = abs(lat_end - lat_start)
    
    ncols = float(grid_size[0]) #i, j dimensions of grid
    nrows = float(grid_size[1])
    
    cell_i = lon_len/ncols #i,j dimensions of individual grid cells 
    cell_j = lat_len/nrows


    #Add (lon, lat, water_usage) tuple to grid using (i, j) key
    for (lon,lat,water) in tuple_list:
        #Calculate (i,j) values from lon, lat values
        if lon_start < i_start:
            i = int((lon+lon_offset)/cell_i)
        else:
            i = int((lon - lon_offset)/cell_i)

        if lat_start < j_start: 
            j = int((lat +lat_offset)/cell_j)
        else:
            j = int((lat - lat_offset)/cell_j)

        #Reassign points on upper boundaries to previous grid cell
        if i==i_end:
            i = i_end - 1
        if j==j_end:
            j = j_end-1

        #Only add cells to dictionary if within grid boundaries. Include edges.
        #Print warning message if not in boundary. 
        if (i>=i_start and i<i_end) and (j>=j_start and j<j_end):
            #For existing cells, add new water usage value to total.     
            if (i,j) in grid:
                grid[(i,j)] += water 
            #Otherwise create new dictionary entry. 
            else:
                grid[(i,j)] = water
        else:
            print("(%d, %d) is located outside of the grid boundary and will be excluded." %(i, j))

    return(grid)


def pplnt_convertjson(json_input):
    """Converts dictionary of powerplant data to (lon, lat, water-usage) tuples.

    Arguments:

        json_input - dictionary of powerplant data, in geoJSON feature
                     collection format.  The key "features"
                     corresponds to a list of individual power plants,
                     which each have "geometry" and "properties"
                     attributes. The key ["geometry"]["coordinates"]
                     contains a (longitude, latitude) tuple, in that
                     order, while the ["properties"]["water-usage"]
                     key corresponds to water usage data.

    Return value: a list of tuples of three elements:(lon, lat,
                  water-usage). Each tuple represents an individual
                  powerplant.
    """

    #Get list of plants
    plantlist = json_input["features"]

    #Create and append tuples of lon, lat, and water usage
    output = [(plant["geometry"]["coordinates"][0], plant["geometry"]["coordinates"][1],
               plant["properties"]["water-usage"]) for plant in plantlist]
    
    return(output)

def pplnt_writecsv(grid_as_dict, filename, comment=None):
    """Write dictionary representation of frid to csv.

    Arguments:
      
      grid_as_dict - dictionary indexed with (row,column) tuples and
                     grid cell values as values.

      filename - name of output file

      comment - (OPTIONAL) descriptive string to be written in the
                first line of output.  If none, a default will be used
                (i.e., the csv data always starts on line 2).

    """
    
    outfile = open(filename, 'w')          # python3 note:  should use newline=''
    if comment is None:
        outfile.write('#power plant data\n')
    else:
        outfile.write('#%s\n'%comment)

    csv_write = csv.writer(outfile, delimiter=',', lineterminator='\n') # lineterminator= not needed in python3 (see comment above)
    csvrows = ((key[0],key[1],value) for key,value in grid_as_dict.iteritems())
    csv_write.writerows(csvrows)

    outfile.close()

def convert_capacity(plant):
    """Converts capacity value of power plant from string to float. 

    Arguments:
        plant - A geoJSON object denoting an individual power plant. 
    
    Return value: The capacity of the power plant, as a float.
    """

    capacity = plant["properties"]["capacity"]
    capacity = float(capacity.replace("MWe",""))                
    return(capacity)
    
def getWaterUsage(file1, water_conversion_dict):
    """Calculates water usage factors for power plants.

    Water usage for each plant is calculated from plant capacity and type
    of fuel. Plant data is initially in geoJSON format (a feature collection where
    each feature is an individual power plant). Individual plants are listed within
    the "features" key, and each plant has "geometry" and "properties" attributes.
    This data is converted to a Python dictionary with water usage data appended to
    each plant's "properties" attribute.

    Arguments:
        file1   - The file handle of the geoJSON data.
        water_conversion_dict
                - A dictionary of water usage conversion factors. Each
                key is a type of fuel, and the corresponding value is the water
                usage factor for that fuel (in km^3/MWe).

    Return value: A Python dictionary of geoJSON power plant data, updated
                with water usage data for each plant.  
        
    """

    #Load original geoJSON file. This is the plant dictionary. 
    raw_json = json.load(file1) 
     
    #Multiply plant capacity (MWe) by water usage factor (km^3/MWe) from dictionary to get list of water usage data. 
    #Add this data to plant dictionary. 
    for plant in raw_json["features"]:
        plant["properties"]["water-usage"] = convert_capacity(plant)*water_conversion_dict[plant["properties"]["fuel"]] 
    
    return(raw_json)   #Returns updated dictionary of plants and features.  

