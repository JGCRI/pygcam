OPT    =  -O3 -g
CFLAGS = $(OPT) -I$(NETCDF_INCLUDE) -std=c99 
LDFLAGS = -L$(NETCDF_LIB) -Wl,-rpath,$(NETCDF_LIB)
LIBS   = -lnetcdf -lm


mat2nc: mat2nc.o
	gcc $(LDFLAGS) -o mat2nc mat2nc.o $(LIBS)
