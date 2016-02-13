#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <netcdf.h> 

#define NLAT 360
#define NLON 720
#define NYEAR 18

// max length of a configuration line, in characters
#define MAXLEN 1024
// number of regions
#define NRGN 63
// number of water basins
#define NBASIN 235


/* the file names in the output file are:
 *  0  - output file
 *  1  - water supply file
 *  2  - irrigation demand file
 *  3  - livestock demand file
 *  4  - electricity demand file
 *  5  - manufacturing demand file
 *  6  - total demand file
 *  7  - domestic demand file
 *  8  - water scarcity index file
 *  9  - population file
 *  10 - basin-level supply
 *  11 - basin-level irrigation demand
 *  12 - basin-level livestock demand
 *  13 - basin-level electricity demand
 *  14 - basin-level mfg demand
 *  15 - basin-level total demand
 *  16 - basin-level domestic demand
 *  17 - basin-level wsi
 *  18 - region-level supply
 *  19 - region-level irrigation demand
 *  20 - region-level livestock demand
 *  21 - region-level electricity demand
 *  22 - region-level mfg demand
 *  23 - region-level total demand
 *  24 - region-level domestic demand
 *  25 - region-level wsi

 */
// some constants for dealing with the files
enum filenum {OUTPUT=0,
              G_SUPPLY, G_IRR, G_LIV, G_ELEC, G_MFG, G_TOT, G_DOM, G_WSI,   // gridded inputs
              POP,                                                   // population table
              B_SUPPLY, B_IRR, B_LIV, B_ELEC, B_MFG, B_TOT, B_DOM, B_WSI,  // basin tables
              R_SUPPLY, R_IRR, R_LIV, R_ELEC, R_MFG, R_TOT, R_DOM, R_WSI}; // region tables

// number of gridded data inputs
#define NGRIDI 8
// number of basin data inputs (not to be confused with NBASIN above)
#define NBASINI 8
// number of region data inputs
#define NRGNI 8

/* Region name table:                 // XXX this is wrong.  need to correct.
   0 - Africa
   1 - Australia
   2 - Canada
   3 - China
   4 - Eastern Europe
   5 - Former Soviet Union
   6 - India
   7 - Japan
   8 - Korea
   9 - Latin America
   10 - Middle East
   11 - Southeast Asia
   12 - USA
   13 - Western Europe
*/

struct metadata {
  // metadata for the run
  float global_forcing;
  float global_pop;
  float global_pcgdp;
  char  scenario[11];           // coded scenario designator
};


void
check_err(const int stat, const int line, const char *file) {
    if (stat != NC_NOERR) {
        (void)fprintf(stderr,"line %d of %s: %s\n", line, file, nc_strerror(stat));
        fflush(stderr);
        exit(1);
    }
}

/* pointer to an array of NLAT x NLON matrices */
typedef float (*datasliceptr)[NLAT][NLON]; 
/* read data, aggregate, and transpose */
int read_file_name(FILE *cfg, char *fn);
int read_and_aggregate_data(const char *filename, datasliceptr data);
int read_5yr_data(const char *filename, datasliceptr data, int nskipyr);
int mat2nc(const char *outfilename, const struct metadata *md,
           const float *supply, const float *irr_dmd, const float *livestock_dmd,
           const float *elec_dmd, const float *mfg_dmd, const float *total_dmd,
           const float *dom_dmd, const float *scarcity, const int *pop,
           const float *bsupply, const float *birr, const float *bliv,
           const float *belec, const float *bmfg, const float *btotal,
           const float *bdom, const float *bwsi,
           const float *rsupply, const float *rirr, const float *rliv,
           const float *relec, const float *rmfg, const float *rtotal,
           const float *rdom, const float *rwsi);

int read_pop_data(const char *filename, int popdata[][NRGN]);
int read_table_data(const char *filename, int nrow, float *data); /* basin-level or region-level tables */

int main(int argc, char *argv[])
{
  FILE *infile;
  struct metadata md;
  char filename[MAXLEN];
  char outfilename[MAXLEN];     // name of the output file
  static float data[NGRIDI][NYEAR][NLAT][NLON];
  int popdata[NYEAR][NRGN];
  static float bdata[NBASINI][NYEAR][NBASIN];
  static float rdata[NRGNI][NYEAR][NRGN];
  int nread, stat, i, nskipyr;

  if(argc == 2) {
    if(argv[1][0] == '-') {
      infile = stdin;
      fprintf(stderr, "Reading config from stdin\n");
    }
    else {
      infile = fopen(argv[1], "r");
      if(!infile) {
        fprintf(stderr, "Unable to open file for input: %s\n", argv[1]);
        return 1;
      }
      else
        fprintf(stderr, "Reading config from %s\n", argv[1]);
    }
  }
  else {
    fprintf(stderr, "Usage: %s <infile>\n\t-or-\t%s -\n", argv[0], argv[0]);
    return 2;
  }

  /* read the global attribute values */
  nread =  fscanf(infile, "%f", &md.global_forcing);
  nread += fscanf(infile, "%f", &md.global_pop);
  nread += fscanf(infile, "%f", &md.global_pcgdp);
  // XXX add readin for scenario designator here
  if(nread != 3) {
    fprintf(stderr, "Failed to read global attributes\n");
    fclose(infile);
    return 3;
  }

  stat = read_file_name(infile, outfilename); 
  if(stat)   /* failure: error will be reported in read_file_name */
    return 3;

  /* read the data from the input files and reorganize as necessary */
  /* The first data file is monthly data, so it needs to be treated specially */
  stat = read_file_name(infile, filename);
  if(stat)
    return 3; 
  stat = read_and_aggregate_data(filename, data[0]);
  
  nskipyr = 2;                  /* most inputs have 2 unused years at the beginning */
  for(i=G_IRR;i<=G_WSI;++i) {
    stat = read_file_name(infile, filename);
    if(stat) 
      return 3;
    
    if(i==G_WSI)              /* WSI file */
      nskipyr = 1;              /* WSI input has only 1 unused year */
    stat = read_5yr_data(filename, data[i-G_SUPPLY], nskipyr);
    if(stat)                    /* failure */
      return stat;
  }

  /* read the population data */
  stat = read_file_name(infile, filename);
  if(stat)
    return 3;
  stat = read_pop_data(filename, popdata);
  if(stat)
    return stat;

  for(i=B_SUPPLY; i<=B_WSI; ++i) {
    stat = read_file_name(infile, filename);
    if(stat)
      return 3;

    stat = read_table_data(filename, NBASIN, (float*) bdata[i-B_SUPPLY]);
    if(stat)
      return stat;
  }

  for(i=R_SUPPLY; i<=R_WSI; ++i) {
    stat = read_file_name(infile, filename);
    if(stat)
      return 3;

    stat = read_table_data(filename, NRGN, (float*) rdata[i-R_SUPPLY]);
    if(stat)
      return stat;
  }
  
  /* write out the netcdf files. */
  stat = mat2nc(outfilename, &md, (float*)data[0], (float*)data[1],
                (float*)data[2], (float*)data[3], (float*)data[4],
                (float*)data[5], (float*)data[6], (float*)data[7], (int*)popdata,
                (float*)bdata[0], (float*)bdata[1], (float*)bdata[2],
                (float*)bdata[3], (float*)bdata[4], (float*)bdata[5],
                (float*)bdata[6], (float*)bdata[7],
                (float*)rdata[0], (float*)rdata[1], (float*)rdata[2],
                (float*)rdata[3], (float*)rdata[4], (float*)rdata[5],
                (float*)rdata[6], (float*)rdata[7]);
                
  
  return stat; 
}

/* create water.nc */
/* outfilename is the name of the output file
 * md is a filled-in metadata struct
 * the remaining args are the data arrays.  They should be organized like so:
 *               data[NYEAR][NLAT][NLON]
 * 
 */
int mat2nc(const char *outfilename, const struct metadata *md,
           const float *supply, const float *irr_dmd, const float *livestock_dmd,
           const float *elec_dmd, const float *mfg_dmd, const float *total_dmd,
           const float *dom_dmd, const float *scarcity, const int *pop,
           const float *bsupply, const float *birr, const float *bliv,
           const float *belec, const float *bmfg, const float *btot,
           const float *bdom, const float *bwsi,
           const float *rsupply, const float *rirr, const float *rliv,
           const float *relec, const float *rmfg, const float *rtot,
           const float *rdom, const float *rwsi)
{

    int i;
  
    int  stat;  /* return status */
    int  ncid;  /* netCDF id */

    /* dimension ids */
    int lat_dim;
    int lon_dim;
    int time_dim;
    int rgn_dim;
    int basin_dim;

    /* dimension lengths */
    size_t lat_len = NLAT;
    size_t lon_len = NLON;
    size_t time_len = NYEAR;
    size_t rgn_len = NRGN;
    size_t basin_len = NBASIN;

    /* variable ids */
    int lat_id;
    int lon_id;
    int time_id;
    int rgn_id;
    int basin_id;
    int supply_id;
    int irrigation_demand_id;
    int livestock_demand_id;
    int electricity_demand_id;
    int mfg_demand_id;
    int total_demand_id;
    int domestic_demand_id;
    int scarcity_id;
    int pop_id;
    int bs_id, birr_id, bliv_id, belec_id, bmfg_id, btot_id, bdom_id, bwsi_id;
    int rs_id, rirr_id, rliv_id, relec_id, rmfg_id, rtot_id, rdom_id, rwsi_id; 

    /* rank (number of dimensions) for each variable */
#   define RANK_lat 1
#   define RANK_lon 1
#   define RANK_time 1
#define RANK_rgn 1 
#   define RANK_supply 3
#   define RANK_irrigation_demand 3
#   define RANK_livestock_demand 3
#   define RANK_electricity_demand 3
#   define RANK_mfg_demand 3
#   define RANK_total_demand 3
#   define RANK_domestic_demand 3
#   define RANK_scarcity 3
#define RANK_pop 2
#define RANK_basin 1
#define RANK_basin_tbl 2
    /* All of the basin quantities will be reused, since all of the
       basin tables have the same shape */

    /* variable shapes */
    int lat_dims[RANK_lat];
    int lon_dims[RANK_lon];
    int time_dims[RANK_time];
    int rgn_dims[RANK_rgn];
    int supply_dims[RANK_supply];
    int irrigation_demand_dims[RANK_irrigation_demand];
    int livestock_demand_dims[RANK_livestock_demand];
    int electricity_demand_dims[RANK_electricity_demand];
    int mfg_demand_dims[RANK_mfg_demand];
    int total_demand_dims[RANK_total_demand];
    int domestic_demand_dims[RANK_domestic_demand];
    int scarcity_dims[RANK_scarcity];
    int pop_dims[RANK_pop];
    int basin_dims[RANK_basin];
    int basin_tbl_dims[RANK_basin_tbl]; 

    /* enter define mode */
    stat = nc_create(outfilename, NC_CLOBBER, &ncid);
    check_err(stat,__LINE__,__FILE__);

    /* define dimensions */
    stat = nc_def_dim(ncid, "lat", lat_len, &lat_dim);
    check_err(stat,__LINE__,__FILE__);
    stat = nc_def_dim(ncid, "lon", lon_len, &lon_dim);
    check_err(stat,__LINE__,__FILE__);
    stat = nc_def_dim(ncid, "time", time_len, &time_dim);
    check_err(stat,__LINE__,__FILE__);
    stat = nc_def_dim(ncid, "rgn", rgn_len, &rgn_dim);
    check_err(stat,__LINE__,__FILE__);
    stat = nc_def_dim(ncid, "basin", basin_len, &basin_dim);
    check_err(stat,__LINE__,__FILE__);
    
    /* define variables */

    lat_dims[0] = lat_dim;
    stat = nc_def_var(ncid, "lat", NC_FLOAT, RANK_lat, lat_dims, &lat_id);
    check_err(stat,__LINE__,__FILE__);

    lon_dims[0] = lon_dim;
    stat = nc_def_var(ncid, "lon", NC_FLOAT, RANK_lon, lon_dims, &lon_id);
    check_err(stat,__LINE__,__FILE__);

    time_dims[0] = time_dim;
    stat = nc_def_var(ncid, "time", NC_FLOAT, RANK_time, time_dims, &time_id);
    check_err(stat,__LINE__,__FILE__);

    rgn_dims[0] = rgn_dim;
    stat = nc_def_var(ncid, "rgn", NC_INT, RANK_rgn, rgn_dims, &rgn_id);
    check_err(stat,__LINE__,__FILE__);

    basin_dims[0] = basin_dim;
    stat = nc_def_var(ncid, "basin", NC_INT, RANK_basin, basin_dims, &basin_id);
    check_err(stat,__LINE__,__FILE__);    

    supply_dims[0] = time_dim;
    supply_dims[1] = lat_dim;
    supply_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "supply", NC_FLOAT, RANK_supply, supply_dims, &supply_id);
    check_err(stat,__LINE__,__FILE__);

    irrigation_demand_dims[0] = time_dim;
    irrigation_demand_dims[1] = lat_dim;
    irrigation_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "irrigation_demand", NC_FLOAT, RANK_irrigation_demand, irrigation_demand_dims, &irrigation_demand_id);
    check_err(stat,__LINE__,__FILE__);

    livestock_demand_dims[0] = time_dim;
    livestock_demand_dims[1] = lat_dim;
    livestock_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "livestock_demand", NC_FLOAT, RANK_livestock_demand, livestock_demand_dims, &livestock_demand_id);
    check_err(stat,__LINE__,__FILE__);

    electricity_demand_dims[0] = time_dim;
    electricity_demand_dims[1] = lat_dim;
    electricity_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "electricity_demand", NC_FLOAT, RANK_electricity_demand, electricity_demand_dims, &electricity_demand_id);
    check_err(stat,__LINE__,__FILE__);

    mfg_demand_dims[0] = time_dim;
    mfg_demand_dims[1] = lat_dim;
    mfg_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "mfg_demand", NC_FLOAT, RANK_mfg_demand, mfg_demand_dims, &mfg_demand_id);
    check_err(stat,__LINE__,__FILE__);

    total_demand_dims[0] = time_dim;
    total_demand_dims[1] = lat_dim;
    total_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "total_demand", NC_FLOAT, RANK_total_demand, total_demand_dims, &total_demand_id);
    check_err(stat,__LINE__,__FILE__);

    domestic_demand_dims[0] = time_dim;
    domestic_demand_dims[1] = lat_dim;
    domestic_demand_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "domestic_demand", NC_FLOAT, RANK_domestic_demand, domestic_demand_dims, &domestic_demand_id);
    check_err(stat,__LINE__,__FILE__);

    scarcity_dims[0] = time_dim;
    scarcity_dims[1] = lat_dim;
    scarcity_dims[2] = lon_dim;
    stat = nc_def_var(ncid, "scarcity", NC_FLOAT, RANK_scarcity, scarcity_dims, &scarcity_id);
    check_err(stat,__LINE__,__FILE__);

    pop_dims[0] = time_dim;
    pop_dims[1] = rgn_dim;
    stat = nc_def_var(ncid, "population", NC_INT, RANK_pop, pop_dims, &pop_id);
    check_err(stat, __LINE__, __FILE__);

    basin_tbl_dims[0] = time_dim;
    basin_tbl_dims[1] = basin_dim;
    stat = nc_def_var(ncid, "basin_supply", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &bs_id);
    check_err(stat, __LINE__, __FILE__);
    /* other basin-level vars follow the same basic plan */
    stat = nc_def_var(ncid, "basin_irrigation_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &birr_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_livestock_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &bliv_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_electricity_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &belec_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_manufacturing_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &bmfg_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_total_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &btot_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_domestic_demand", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &bdom_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "basin_water_scarcity", NC_FLOAT, RANK_basin_tbl, basin_tbl_dims, &bwsi_id);
    check_err(stat, __LINE__, __FILE__); 

    /* region-level variables follow the same plan as the population table */
    stat = nc_def_var(ncid, "region_supply", NC_FLOAT, RANK_pop, pop_dims, &rs_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_irrigation_demand", NC_FLOAT, RANK_pop, pop_dims, &rirr_id);
    check_err(stat, __LINE__, __FILE__); 
    stat = nc_def_var(ncid, "region_livestock_demand", NC_FLOAT, RANK_pop, pop_dims, &rliv_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_electricity_demand", NC_FLOAT, RANK_pop, pop_dims, &relec_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_manufacturing_demand", NC_FLOAT, RANK_pop, pop_dims, &rmfg_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_total", NC_FLOAT, RANK_pop, pop_dims, &rtot_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_domestic_demand", NC_FLOAT, RANK_pop, pop_dims, &rdom_id);
    check_err(stat, __LINE__, __FILE__);
    stat = nc_def_var(ncid, "region_water_scarcity", NC_FLOAT, RANK_pop, pop_dims, &rwsi_id);
    check_err(stat, __LINE__, __FILE__);
    
    /* assign global attributes */
    { /* forcing */
    stat = nc_put_att_float(ncid, NC_GLOBAL, "forcing", NC_FLOAT, 1, &md->global_forcing);
    check_err(stat,__LINE__,__FILE__);
    }
    { /* population */
    stat = nc_put_att_float(ncid, NC_GLOBAL, "population", NC_FLOAT, 1, &md->global_pop);
    check_err(stat,__LINE__,__FILE__);
    }
#if 0
    { /* pcGDP */
    stat = nc_put_att_float(ncid, NC_GLOBAL, "pcGDP", NC_FLOAT, 1, &md->global_pcgdp);
    check_err(stat,__LINE__,__FILE__);
    }
#endif

    /* assign per-variable attributes */
    { /* units */
    stat = nc_put_att_text(ncid, lat_id, "units", 13, "degrees_north");
    check_err(stat,__LINE__,__FILE__);
    }
    { /* units */
    stat = nc_put_att_text(ncid, lon_id, "units", 12, "degrees_east");
    check_err(stat,__LINE__,__FILE__);
    }
    { /* units */
    stat = nc_put_att_text(ncid, time_id, "units", 4, "year");
    check_err(stat,__LINE__,__FILE__);
    }
    stat = nc_put_att_text(ncid, pop_id, "units", 9, "thousands");
    check_err(stat,__LINE__,__FILE__);

    /* supply and demand have units of km^3 */
    stat = nc_put_att_text(ncid, supply_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, irrigation_demand_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, livestock_demand_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, electricity_demand_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, mfg_demand_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, total_demand_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, domestic_demand_id, "units", 4 , "km^3");

    stat = nc_put_att_text(ncid, bs_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, birr_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, bliv_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, belec_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, bmfg_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, btot_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, bdom_id, "units", 4 , "km^3");

    stat = nc_put_att_text(ncid, rs_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, rirr_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, rliv_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, relec_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, rmfg_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, rtot_id, "units", 4 , "km^3");
    stat = nc_put_att_text(ncid, rdom_id, "units", 4 , "km^3");


    /* wsi is unitless */
    stat = nc_put_att_text(ncid, scarcity_id, "units", 10 , "(unitless)");
    stat = nc_put_att_text(ncid, bwsi_id, "units", 10 , "(unitless)");
    stat = nc_put_att_text(ncid, rwsi_id, "units", 10 , "(unitless)"); 

    /* leave define mode */
    stat = nc_enddef (ncid);
    check_err(stat,__LINE__,__FILE__);

    /* assign variable data */
    {
    float lat_data[NLAT] = {-89.75, -89.25, -88.75, -88.25, -87.75, -87.25, -86.75, -86.25, -85.75, -85.25, -84.75, -84.25, -83.75, -83.25, -82.75, -82.25, -81.75, -81.25, -80.75, -80.25, -79.75, -79.25, -78.75, -78.25, -77.75, -77.25, -76.75, -76.25, -75.75, -75.25, -74.75, -74.25, -73.75, -73.25, -72.75, -72.25, -71.75, -71.25, -70.75, -70.25, -69.75, -69.25, -68.75, -68.25, -67.75, -67.25, -66.75, -66.25, -65.75, -65.25, -64.75, -64.25, -63.75, -63.25, -62.75, -62.25, -61.75, -61.25, -60.75, -60.25, -59.75, -59.25, -58.75, -58.25, -57.75, -57.25, -56.75, -56.25, -55.75, -55.25, -54.75, -54.25, -53.75, -53.25, -52.75, -52.25, -51.75, -51.25, -50.75, -50.25, -49.75, -49.25, -48.75, -48.25, -47.75, -47.25, -46.75, -46.25, -45.75, -45.25, -44.75, -44.25, -43.75, -43.25, -42.75, -42.25, -41.75, -41.25, -40.75, -40.25, -39.75, -39.25, -38.75, -38.25, -37.75, -37.25, -36.75, -36.25, -35.75, -35.25, -34.75, -34.25, -33.75, -33.25, -32.75, -32.25, -31.75, -31.25, -30.75, -30.25, -29.75, -29.25, -28.75, -28.25, -27.75, -27.25, -26.75, -26.25, -25.75, -25.25, -24.75, -24.25, -23.75, -23.25, -22.75, -22.25, -21.75, -21.25, -20.75, -20.25, -19.75, -19.25, -18.75, -18.25, -17.75, -17.25, -16.75, -16.25, -15.75, -15.25, -14.75, -14.25, -13.75, -13.25, -12.75, -12.25, -11.75, -11.25, -10.75, -10.25, -9.75, -9.25, -8.75, -8.25, -7.75, -7.25, -6.75, -6.25, -5.75, -5.25, -4.75, -4.25, -3.75, -3.25, -2.75, -2.25, -1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25, 6.75, 7.25, 7.75, 8.25, 8.75, 9.25, 9.75, 10.25, 10.75, 11.25, 11.75, 12.25, 12.75, 13.25, 13.75, 14.25, 14.75, 15.25, 15.75, 16.25, 16.75, 17.25, 17.75, 18.25, 18.75, 19.25, 19.75, 20.25, 20.75, 21.25, 21.75, 22.25, 22.75, 23.25, 23.75, 24.25, 24.75, 25.25, 25.75, 26.25, 26.75, 27.25, 27.75, 28.25, 28.75, 29.25, 29.75, 30.25, 30.75, 31.25, 31.75, 32.25, 32.75, 33.25, 33.75, 34.25, 34.75, 35.25, 35.75, 36.25, 36.75, 37.25, 37.75, 38.25, 38.75, 39.25, 39.75, 40.25, 40.75, 41.25, 41.75, 42.25, 42.75, 43.25, 43.75, 44.25, 44.75, 45.25, 45.75, 46.25, 46.75, 47.25, 47.75, 48.25, 48.75, 49.25, 49.75, 50.25, 50.75, 51.25, 51.75, 52.25, 52.75, 53.25, 53.75, 54.25, 54.75, 55.25, 55.75, 56.25, 56.75, 57.25, 57.75, 58.25, 58.75, 59.25, 59.75, 60.25, 60.75, 61.25, 61.75, 62.25, 62.75, 63.25, 63.75, 64.25, 64.75, 65.25, 65.75, 66.25, 66.75, 67.25, 67.75, 68.25, 68.75, 69.25, 69.75, 70.25, 70.75, 71.25, 71.75, 72.25, 72.75, 73.25, 73.75, 74.25, 74.75, 75.25, 75.75, 76.25, 76.75, 77.25, 77.75, 78.25, 78.75, 79.25, 79.75, 80.25, 80.75, 81.25, 81.75, 82.25, 82.75, 83.25, 83.75, 84.25, 84.75, 85.25, 85.75, 86.25, 86.75, 87.25, 87.75, 88.25, 88.75, 89.25, 89.75} ;
    size_t lat_startset[1] = {0} ;
    size_t lat_countset[1] = {NLAT} ;
    stat = nc_put_vara(ncid, lat_id, lat_startset, lat_countset, lat_data);
    check_err(stat,__LINE__,__FILE__);
    }

    {
    float lon_data[NLON] = {-179.75, -179.25, -178.75, -178.25, -177.75, -177.25, -176.75, -176.25, -175.75, -175.25, -174.75, -174.25, -173.75, -173.25, -172.75, -172.25, -171.75, -171.25, -170.75, -170.25, -169.75, -169.25, -168.75, -168.25, -167.75, -167.25, -166.75, -166.25, -165.75, -165.25, -164.75, -164.25, -163.75, -163.25, -162.75, -162.25, -161.75, -161.25, -160.75, -160.25, -159.75, -159.25, -158.75, -158.25, -157.75, -157.25, -156.75, -156.25, -155.75, -155.25, -154.75, -154.25, -153.75, -153.25, -152.75, -152.25, -151.75, -151.25, -150.75, -150.25, -149.75, -149.25, -148.75, -148.25, -147.75, -147.25, -146.75, -146.25, -145.75, -145.25, -144.75, -144.25, -143.75, -143.25, -142.75, -142.25, -141.75, -141.25, -140.75, -140.25, -139.75, -139.25, -138.75, -138.25, -137.75, -137.25, -136.75, -136.25, -135.75, -135.25, -134.75, -134.25, -133.75, -133.25, -132.75, -132.25, -131.75, -131.25, -130.75, -130.25, -129.75, -129.25, -128.75, -128.25, -127.75, -127.25, -126.75, -126.25, -125.75, -125.25, -124.75, -124.25, -123.75, -123.25, -122.75, -122.25, -121.75, -121.25, -120.75, -120.25, -119.75, -119.25, -118.75, -118.25, -117.75, -117.25, -116.75, -116.25, -115.75, -115.25, -114.75, -114.25, -113.75, -113.25, -112.75, -112.25, -111.75, -111.25, -110.75, -110.25, -109.75, -109.25, -108.75, -108.25, -107.75, -107.25, -106.75, -106.25, -105.75, -105.25, -104.75, -104.25, -103.75, -103.25, -102.75, -102.25, -101.75, -101.25, -100.75, -100.25, -99.75, -99.25, -98.75, -98.25, -97.75, -97.25, -96.75, -96.25, -95.75, -95.25, -94.75, -94.25, -93.75, -93.25, -92.75, -92.25, -91.75, -91.25, -90.75, -90.25, -89.75, -89.25, -88.75, -88.25, -87.75, -87.25, -86.75, -86.25, -85.75, -85.25, -84.75, -84.25, -83.75, -83.25, -82.75, -82.25, -81.75, -81.25, -80.75, -80.25, -79.75, -79.25, -78.75, -78.25, -77.75, -77.25, -76.75, -76.25, -75.75, -75.25, -74.75, -74.25, -73.75, -73.25, -72.75, -72.25, -71.75, -71.25, -70.75, -70.25, -69.75, -69.25, -68.75, -68.25, -67.75, -67.25, -66.75, -66.25, -65.75, -65.25, -64.75, -64.25, -63.75, -63.25, -62.75, -62.25, -61.75, -61.25, -60.75, -60.25, -59.75, -59.25, -58.75, -58.25, -57.75, -57.25, -56.75, -56.25, -55.75, -55.25, -54.75, -54.25, -53.75, -53.25, -52.75, -52.25, -51.75, -51.25, -50.75, -50.25, -49.75, -49.25, -48.75, -48.25, -47.75, -47.25, -46.75, -46.25, -45.75, -45.25, -44.75, -44.25, -43.75, -43.25, -42.75, -42.25, -41.75, -41.25, -40.75, -40.25, -39.75, -39.25, -38.75, -38.25, -37.75, -37.25, -36.75, -36.25, -35.75, -35.25, -34.75, -34.25, -33.75, -33.25, -32.75, -32.25, -31.75, -31.25, -30.75, -30.25, -29.75, -29.25, -28.75, -28.25, -27.75, -27.25, -26.75, -26.25, -25.75, -25.25, -24.75, -24.25, -23.75, -23.25, -22.75, -22.25, -21.75, -21.25, -20.75, -20.25, -19.75, -19.25, -18.75, -18.25, -17.75, -17.25, -16.75, -16.25, -15.75, -15.25, -14.75, -14.25, -13.75, -13.25, -12.75, -12.25, -11.75, -11.25, -10.75, -10.25, -9.75, -9.25, -8.75, -8.25, -7.75, -7.25, -6.75, -6.25, -5.75, -5.25, -4.75, -4.25, -3.75, -3.25, -2.75, -2.25, -1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25, 6.75, 7.25, 7.75, 8.25, 8.75, 9.25, 9.75, 10.25, 10.75, 11.25, 11.75, 12.25, 12.75, 13.25, 13.75, 14.25, 14.75, 15.25, 15.75, 16.25, 16.75, 17.25, 17.75, 18.25, 18.75, 19.25, 19.75, 20.25, 20.75, 21.25, 21.75, 22.25, 22.75, 23.25, 23.75, 24.25, 24.75, 25.25, 25.75, 26.25, 26.75, 27.25, 27.75, 28.25, 28.75, 29.25, 29.75, 30.25, 30.75, 31.25, 31.75, 32.25, 32.75, 33.25, 33.75, 34.25, 34.75, 35.25, 35.75, 36.25, 36.75, 37.25, 37.75, 38.25, 38.75, 39.25, 39.75, 40.25, 40.75, 41.25, 41.75, 42.25, 42.75, 43.25, 43.75, 44.25, 44.75, 45.25, 45.75, 46.25, 46.75, 47.25, 47.75, 48.25, 48.75, 49.25, 49.75, 50.25, 50.75, 51.25, 51.75, 52.25, 52.75, 53.25, 53.75, 54.25, 54.75, 55.25, 55.75, 56.25, 56.75, 57.25, 57.75, 58.25, 58.75, 59.25, 59.75, 60.25, 60.75, 61.25, 61.75, 62.25, 62.75, 63.25, 63.75, 64.25, 64.75, 65.25, 65.75, 66.25, 66.75, 67.25, 67.75, 68.25, 68.75, 69.25, 69.75, 70.25, 70.75, 71.25, 71.75, 72.25, 72.75, 73.25, 73.75, 74.25, 74.75, 75.25, 75.75, 76.25, 76.75, 77.25, 77.75, 78.25, 78.75, 79.25, 79.75, 80.25, 80.75, 81.25, 81.75, 82.25, 82.75, 83.25, 83.75, 84.25, 84.75, 85.25, 85.75, 86.25, 86.75, 87.25, 87.75, 88.25, 88.75, 89.25, 89.75, 90.25, 90.75, 91.25, 91.75, 92.25, 92.75, 93.25, 93.75, 94.25, 94.75, 95.25, 95.75, 96.25, 96.75, 97.25, 97.75, 98.25, 98.75, 99.25, 99.75, 100.25, 100.75, 101.25, 101.75, 102.25, 102.75, 103.25, 103.75, 104.25, 104.75, 105.25, 105.75, 106.25, 106.75, 107.25, 107.75, 108.25, 108.75, 109.25, 109.75, 110.25, 110.75, 111.25, 111.75, 112.25, 112.75, 113.25, 113.75, 114.25, 114.75, 115.25, 115.75, 116.25, 116.75, 117.25, 117.75, 118.25, 118.75, 119.25, 119.75, 120.25, 120.75, 121.25, 121.75, 122.25, 122.75, 123.25, 123.75, 124.25, 124.75, 125.25, 125.75, 126.25, 126.75, 127.25, 127.75, 128.25, 128.75, 129.25, 129.75, 130.25, 130.75, 131.25, 131.75, 132.25, 132.75, 133.25, 133.75, 134.25, 134.75, 135.25, 135.75, 136.25, 136.75, 137.25, 137.75, 138.25, 138.75, 139.25, 139.75, 140.25, 140.75, 141.25, 141.75, 142.25, 142.75, 143.25, 143.75, 144.25, 144.75, 145.25, 145.75, 146.25, 146.75, 147.25, 147.75, 148.25, 148.75, 149.25, 149.75, 150.25, 150.75, 151.25, 151.75, 152.25, 152.75, 153.25, 153.75, 154.25, 154.75, 155.25, 155.75, 156.25, 156.75, 157.25, 157.75, 158.25, 158.75, 159.25, 159.75, 160.25, 160.75, 161.25, 161.75, 162.25, 162.75, 163.25, 163.75, 164.25, 164.75, 165.25, 165.75, 166.25, 166.75, 167.25, 167.75, 168.25, 168.75, 169.25, 169.75, 170.25, 170.75, 171.25, 171.75, 172.25, 172.75, 173.25, 173.75, 174.25, 174.75, 175.25, 175.75, 176.25, 176.75, 177.25, 177.75, 178.25, 178.75, 179.25, 179.75} ;
    size_t lon_startset[1] = {0} ;
    size_t lon_countset[1] = {NLON} ;
    stat = nc_put_vara(ncid, lon_id, lon_startset, lon_countset, lon_data);
    check_err(stat,__LINE__,__FILE__);
    }

    {
    float time_data[NYEAR] = {2010, 2015, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065, 2070, 2075, 2080, 2085, 2090, 2095} ;
    size_t time_startset[1] = {0} ;
    size_t time_countset[1] = {NYEAR} ;
    stat = nc_put_vara(ncid, time_id, time_startset, time_countset, time_data);
    check_err(stat,__LINE__,__FILE__);
    }

    int rgn_data[NRGN];
    for(i=0;i<NRGN;++i)
      rgn_data[i] = i;
    stat = nc_put_var_int(ncid, rgn_id, rgn_data);
    check_err(stat,__LINE__,__FILE__);

    int basin_data[NBASIN];
    for(i=0; i<NBASIN; ++i)
      basin_data[i] = i+1;
    stat = nc_put_var_int(ncid, basin_id, basin_data);
    check_err(stat, __LINE__, __FILE__);
    
    /* write out the data variables */
    stat = nc_put_var_float(ncid, supply_id, supply);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, irrigation_demand_id, irr_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, livestock_demand_id, livestock_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, electricity_demand_id, elec_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, mfg_demand_id, mfg_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, total_demand_id, total_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, domestic_demand_id, dom_dmd);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, scarcity_id, scarcity);
    check_err(stat,__LINE__,__FILE__); 

    stat = nc_put_var_int(ncid, pop_id, pop);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, bs_id, bsupply);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, birr_id, birr);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, bliv_id, bliv);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, belec_id, belec);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, bmfg_id, bmfg);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, btot_id, btot);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, bdom_id, bdom);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, bwsi_id, bwsi);
    check_err(stat,__LINE__,__FILE__);

    
    stat = nc_put_var_float(ncid, rs_id, rsupply);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rirr_id, rirr);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rliv_id, rliv);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, relec_id, relec);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rmfg_id, rmfg);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rtot_id, rtot);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rdom_id, rdom);
    check_err(stat,__LINE__,__FILE__);

    stat = nc_put_var_float(ncid, rwsi_id, rwsi);
    check_err(stat,__LINE__,__FILE__);

    
    stat = nc_close(ncid);
    check_err(stat,__LINE__,__FILE__);
    return 0;
}


int read_and_aggregate_data(const char *filename, datasliceptr data)
{
  /* data is typed as data[NYEAR][NLAT][NLON] */
  int year, iyear, imonth, ilat, ilon, i;
  float fac;
  size_t nread;
  FILE *infile;
  /* The input data is organized as data[t][lon][lat], so we need some buffers
     for reorganizing it */
  static float readdata[12][NLON*NLAT]; /* read buffer */
  static float transdata[NLON*NLAT];      /* transpose buffer */

  if(strcmp(filename,"no-data")==0) {
    /* fill array with NaN */
    for(iyear=0;iyear<NYEAR;++iyear)
      for(ilat=0;ilat<NLAT;++ilat)
        for(ilon=0;ilon<NLON; ++ilon)
          data[iyear][ilat][ilon] = NAN;
    return 0;
  }
  
  infile  = fopen(filename,"rb");
  if(!infile) {
    fprintf(stderr,"Unable to open file %s\n", filename);
    return 1;
  }

  for(year=2001; year <=2095; ++year) {
    nread = fread(readdata, sizeof(float), 12*NLAT*NLON, infile);
    if(nread != 12*NLAT*NLON) {
      fprintf(stderr, "Error reading data from %s in year %d\n",filename,year);
      return 3;
    }
    
    if(year<2010 || year%5 != 0) 
      continue;                 /* skip years before 2010 */

    iyear = (year-2010)/5; 
    
    memset(transdata, 0, NLAT*NLON*sizeof(float));

    /* the input data is a monthly average flow rate in m^3/s.  We
     * need to get an annual average rate, which we'll approximate by
     * averaging the monthly averages (not strictly correct, since the
     * months are different lengths, but it's a small enough error for
     * our purposes).  Then we multiply by the length of a year to get
     * a volume and convert the volume to km^3.  The conversion
     * factors are:
     *      / 12  (monthly average)
     *      * 3.156e7 (seconds in a year)
     *      / 1e9  (m^3 to km^3)
     *   = .00263
     * We'll perform the conversion in the second loop
     */
    for(imonth = 0; imonth < 12; ++imonth)
      for(i=0; i<NLAT*NLON; ++i)
        transdata[i] += readdata[imonth][i];

    fac = 3.156e-2 / 12.0;
    /* transpose the aggregated data */
    for(ilon=0; ilon < NLON; ++ilon)
      for(ilat=0; ilat < NLAT; ++ilat)
        data[iyear][ilat][ilon] = transdata[NLAT*ilon + ilat]*fac; 
  }

  fclose(infile);
  return 0;
}

int read_file_name(FILE *cfg, char *fn)
{
  /* This is a bare-bones reader.  It doesn't check for errant
     whitespace characters, number of characters read, or anything
     like that, so construct your input file carefully. */
  int nr = fscanf(cfg, "%s", fn);
  if(nr==1) {
    printf("Filename is: %s\n",fn);
    return 0; 
  }
  else {
    fprintf(stderr,"Error reading from config file.\n");
    return 1;
  }
}


int read_5yr_data(const char *filename, datasliceptr data, int nskipyr)
{
  /* This is a reader for data that is already given at five-year
     intervals, so all we need to do is skip the years we're not using
     and transpose as required */
  FILE *datafile;
  int iyear, ilat, ilon, nread;
  static float readdata[NYEAR][NLON*NLAT]; /* read buffer */

  if(strcmp(filename,"no-data")==0) {
    /* fill array with NaN */
    for(iyear=0;iyear<NYEAR;++iyear)
      for(ilat=0;ilat<NLAT;++ilat)
        for(ilon=0;ilon<NLON; ++ilon)
          data[iyear][ilat][ilon] = NAN;
    return 0;
  }
  
  datafile = fopen(filename, "rb");
  if(!datafile) {
    fprintf(stderr,"Unable to open file %s for input.\n",filename);
    return 1;
  }

  /* For the data we're working with, nskipyr will be 2 or 3 for the
     data we're using, so we'll assume the readdata array can contain
     the entire block of throwaway.  */
  nread = fread(readdata, sizeof(float), nskipyr*NLAT*NLON, datafile);

  /* read the actual data */
  nread = fread(readdata, sizeof(float), NYEAR*NLAT*NLON, datafile);
  if(nread != NYEAR*NLAT*NLON) {
    fprintf(stderr, "Error reading data from %s.\n", filename);
    return 1;
  }

  for(iyear=0; iyear<NYEAR; ++iyear)
    for(ilon=0; ilon < NLON; ++ilon)
      for(ilat=0; ilat < NLAT; ++ilat)
        data[iyear][ilat][ilon] = readdata[iyear][NLAT*ilon + ilat];

  return 0;
}

int read_pop_data(const char *filename, int data[][NRGN])
{
  FILE *datafile;
  char buf[1024];
  int rgn, iyear;
  int nconv;
  double tmp;
  
  datafile = fopen(filename,"r");
  if(!datafile) {
    fprintf(stderr,"Unable to open file %s for input.\n", filename);
    return 1;
  }

  for(rgn=0; rgn<NRGN; ++rgn) {
    /* drop the first two entries in each line; we don't want
       them. Leave the trailing comma in the input stream. */
    nconv = fscanf(datafile,"%*f,%*f");
    for(iyear=0; iyear<NYEAR; ++iyear) {
      nconv = fscanf(datafile,",%lf", &tmp);
      data[iyear][rgn] = (int) round(tmp);
      if(nconv != 1) {
        fprintf(stderr, "Error reading data from %s .  rgn= %d  iyear = %d\n",
                filename, rgn, iyear);
        fclose(datafile);
        return 1;
      }
    }
    /* drop the remainder of the line (necessary when there are additional years in the file). */
    fgets(buf, 1024, datafile);
  }

  fclose(datafile);
  return 0;
}

int read_table_data(const char *filename, int nrow, float *data)
{
  /* data = data[NYEAR][nrow], where nrow will be either NBASIN or NRGN */
  /* The original matlab data was a nrow x (NYEAR+1) matrix.  We want
     NYEAR x nrow, which is the transpose, but matlab also stores
     its outputs in column order rather than row, so the two
     transposes cancel out, meaning that we can read the data in with
     no transpose. */
  FILE *datafile;
  /* XXX this next declaration relies on the fact that NBASIN > NRGN */
  float tempdata[NBASIN]; /* there is an extra year in the input (2005) that we have to skip */
  int ibasin, iyear, nread;

  datafile = fopen(filename,"r");
  if(!datafile) {
    fprintf(stderr,"Unable to open file %s for input.\n", filename);
    return 1;
  }

  nread = fread(tempdata, sizeof(float), nrow, datafile); /* this is the throwaway year */
  nread = fread(data, sizeof(float), NYEAR*nrow, datafile);
  if(nread != NYEAR*nrow) {
    fprintf(stderr,"Error reading data from file %s\n", filename);
    return 1;
  }

  return 0; 
}
