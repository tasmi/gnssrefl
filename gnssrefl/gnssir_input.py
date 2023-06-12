import argparse
import json
import os
import subprocess
import sys

import gnssrefl.gps as g

from gnssrefl.utils import str2bool


def parse_arguments():
    # user inputs the observation file information
    parser = argparse.ArgumentParser()
    # required arguments
    parser.add_argument("station", help="station (lowercase)", type=str)
    parser.add_argument("-lat", help="Latitude (degrees)", type=float)
    parser.add_argument("-lon", help="Longitude (degrees)", type=float)
    parser.add_argument("-height", help="Ellipsoidal height (meters)", type=float)
    parser.add_argument("-e1", default=None, type=int, help="Lower limit elevation angle (deg),default 5")
    parser.add_argument("-e2", default=None, type=int, help="Upper limit elevation angle (deg), default 25")
    parser.add_argument("-h1", default=None, type=float, help="Lower limit reflector height (m), default 0.5")
    parser.add_argument("-h2", default=None, type=float, help="Upper limit reflector height (m), default 8")
    parser.add_argument("-nr1",default=None, type=float, help="Lower limit RH used for noise region in QC(m)")
    parser.add_argument("-nr2",default=None, type=float, help="Upper limit RH used for noise region in QC(m)")
    parser.add_argument("-peak2noise", default=None, type=float, help="peak to noise ratio used for QC")
    parser.add_argument("-ampl", default=None, type=float, help="Required spectral peak amplitude for QC")
    parser.add_argument("-allfreq", default=None, type=str, help="Set to True to include all GNSS")
    parser.add_argument("-l1", default=None, type=str, help="Only use GPS L1")
    parser.add_argument("-l2c", default=None, type=str, help="Only use GPS L2C")
    parser.add_argument("-xyz", default=None, type=str, help="True if using Cartesian coordinates")
    parser.add_argument("-refraction", default=None, type=str, help="Set to False to turn off refraction correction")
    parser.add_argument("-extension", type=str, help="Provide extension name so you can try different strategies")
    parser.add_argument("-ediff", default=None, type=str, help="Allowed min/max elevation diff from obs min/max elev angle (degrees) default is 2")
    parser.add_argument("-delTmax", default=None, type=float, help="max arc length (min) default is 75. Shorten for tides.")
    parser.add_argument('-frlist', nargs="*",type=int,  help="User defined frequencies using our nomenclature.")
    parser.add_argument('-azlist2', nargs="*",type=float,  help="Azimuth list, default 0-360") 


    args = parser.parse_args().__dict__

    # convert all expected boolean inputs from strings to booleans
    boolean_args = ['allfreq', 'l1', 'l2c', 'xyz', 'refraction']
    args = str2bool(args, boolean_args)

    # only return a dictionary of arguments that were added from the user - all other defaults will be set in code below
    return {key: value for key, value in args.items() if value is not None}


def make_gnssir_input(station: str, lat: float=0, lon: float=0, height: float=0, e1: int = 5, e2: int = 25,
              h1: float = 0.5, h2: float = 8.0, nr1: float = None, nr2: float = None,
              peak2noise: float = 2.8, ampl: float = 5.0, allfreq: bool = False,
              l1: bool = False, l2c: bool = False, xyz: bool = False, refraction: bool = True,
              extension: str = '', ediff: float=2.0, delTmax: float=75.0, frlist: float=[],azlist2: float=[0,360] ):

    """
    This new script sets the Lomb Scargle analysis strategy you will use in gnssir. It saves your inputs 
    to a json file which by default is saved in REFL_CODE/<station>.json. This code is meant to be a replacement
    for make_json_input.

    This version no longer requires you to have azimuth regions of 90-100 degrees. You can set a single set of 
    azimuths in the command line variable azlist2, i.e. -azlist2 0 270 would accommodate all rising and setting arcs 
    between 0 and 270 degrees. If you have multiple distinct regions, that is also acceptable, i.e. -azlist2 0 150 180 360  
    would use all azimuths between 0 and 360 except for 150 to 180

    Your first azimuth constraint can be negative, i.e. -azlist2 -90 90, is allowed.

    Note: you can keep using your old json files - you just need to add this new -azlist2 setting manually.

    Latitude, longitude, and height are assumed to be stored in the UNR database.  If they are not, you should
    set them manually.

    You MUST set -newarcs T when running gnssir to use this new way of selecting rising and setting arcs.
    This allows people to use the old code and the new code, and in principle, the same json file.
    Once the dust has settled, I'll make this way the default.

    Example of a json file that has both the old and new ways. The arrays within the json file are called azval and azval2.
        https://morefunwithgps.com/public_html/sc02.json

    Examples
    --------
    gnssir_input p041 
        uses only GPS frequencies and all azimuths and the coordinates in the UNR database

    gnssir_input p041   -azlist2 0 180 -fr 1 101
        uses UNR coordinates, GPS L1 and Glonass L1 frequencies, and azimuths between 0 and 180.

    gnssir_input p041 -lat 39.9494 -lon -105.19426 -height 1728.85  -l2c T -e1 5 -e2 15
        uses only L2C GPS data between elevation angles of 5 and 15 degrees.
        user input lat/long/height

    gnssir_input p041  -h1 0.5 -h2 10 -e1 5 -e2 25
        uses UNR database, only GPS data between elevation angles of 5-25 degrees and reflector heights of 0.5-10 meters

    gnssir_input p041 -ediff 1
        uses UNR database, only GPS data, default station coordinates, enforces elevation angles to be 
        within 1 degrees of default elevation angle limits (5-25)

    Parameters
    ----------
    station : str
        4 character station ID.
    lat : float, optional
        latitude in degrees.
    lon : float, optional
        longitude in degrees.
    height : float, optional
        ellipsoidal height in meters.
    e1 : int, optional
        elevation angle lower limit in degrees. default is 5.
    e2 : int, optional
        elevation angle upper limit in degrees. default is 25.
    h1 : float, optional
        reflector height lower limit in meters. default is 0.5.
    h2 : float, optional
        reflector height upper limit in meters. default is 8.
    nr1 : float, optional
        noise region lower limit for QC in meters. default is None.
    nr2 : float, optional
        noise region upper limit for QC in meters. default is None.
    peak2noise : float, optional
        peak to noise ratio used for QC.
        default is 2.7 (just a starting point for water - should be 3 or 3.5 for snow or soil...)
    ampl : float, optional
        spectral peak amplitude for QC. default is 6.0
        this is receiver and elevation angle region dependent - so you need to change it based on your site 
    allfreq : bool, optional
        True requests all GNSS frequencies.
        default is False (defaults to use GPS frequencies).
    l1 : bool, optional
        set to True to use only GPS L1 frequency. default is False.
    l2c : bool, optional
        set to use only GPS L2C frequency. default is False.
    xyz : bool, optional
        set to True if using Cartesian coordinates instead of Lat/Long/Ht.
        default is False.
    refraction : bool, optional
        set to False to turn off refraction correction.
        default is True.
    extension : str, optional
        provide extension name so you can try different strategies. 
        Results will then go into $REFL_CODE/YYYY/results/ssss/extension
        Default is '' 
    ediff : float
        quality control parameter (Degrees)
        Allowed min/max elevation angle diff from requested min/max elev angle
        default is 2
    delTmax : float
        maximum allowed arc length (minutes)
        default is 75, which can be a bit long for tides
    frlist : list of integers
        avoids all the booleans - if you know the frequencies, enter them.
        e.g. 1 2 or 1 20 5 or 1 20 101 102
    azlist2 : list of floats
        Default is 0 to 360. subquadrants no longer required , but can be used if necessary

    """

    # make sure environment variables exist
    g.check_environ_variables()

    ns = len(station)
    if ns != 4:
        print('station name must be four characters long. Exiting.')
        sys.exit()

# location of the site - does not have to be very good.  within 100 meters is fine
    query_unr = False
# if you input lat and long as zero ...
    if lat + lon == 0:
        print('Assume you want to use the UNR database.')
        query_unr = True

    if xyz:
        xyz = [lat, lon, height]
        lat, long, height = g.xyz2llhd(xyz)

    if query_unr:
        # try to find the coordinates  at UNR
        lat, lon, height = g.queryUNR_modern(station)
        if lat == 0:
            print('Tried to find coordinates in our UNR database. Not found so exiting')
            sys.exit()

# start the lsp dictionary
    reqA = ampl

    lsp = {}
    lsp['station'] = station.lower()
    lsp['lat'] = lat
    lsp['lon'] = lon
    lsp['ht'] = height

    if h1 > h2:
        print(f'h1 cannot be greater than h2. You have set h1 to {h1} and h2 to {h2}. Exiting.')
        sys.exit()

    if ( (h2-h1)  < 5):
        print(f'h2-h1 must be at least 5 meters apart. You have set h1 to {h1} and h2 to {h2}. Exiting.')
        sys.exit()

    lsp['minH'] = h1 ; lsp['maxH'] = h2 ; lsp['e1'] = e1 ; lsp['e2'] = e2

# the default noise region will the same as the RH exclusion area for now
    if nr1 is None:
        nr1 = h1
    if nr2 is None:
        nr2 = h2

    lsp['NReg'] = [nr1, nr2]
    lsp['PkNoise'] = peak2noise

    # where the instructions will be written
    xdir = os.environ['REFL_CODE']
    outputdir = xdir + '/input'
    if not os.path.isdir(outputdir):
        subprocess.call(['mkdir', outputdir])

    if len(extension) == 0:
        outputfile = outputdir + '/' + station + '.json'
    else:
        outputfile = outputdir + '/' + station + '.' + extension + '.json'

    lsp['polyV'] = 4 # polynomial order for DC removal
    # change this so the min elevation angle for polynomial removal is the same as the 
    # requested analysis region. previously it was hardwired to 5-30
    #lsp['pele'] = [5, 30] # elevation angles used for DC removal
    if (lsp['e1']) < 5:
        usethis = lsp['e1']
        lsp['pele'] = [usethis, 30] # elevation angles used for DC removal
    else:
        lsp['pele'] = [5, 30] # elevation angles used for DC removal
    lsp['ediff'] = ediff # degrees
    lsp['desiredP'] = 0.005 # precision of RH in meters
    # azimuth regions in degrees (in pairs)
    # you can of course have more subdivisions here
    #if (az_list[0]) == 0 & (az_list[-1] == 360):

    N2 = len(azlist2)
    if (N2 % 2) == 0:
        lsp['azval2'] = azlist2
    else:
        print('Illegal azimuth inputs. Must be an even number of azimuth pairs.')
        sys.exit()

    # default frequencies to use - and their required amplitudes. The amplitudes are not set in stone
    # this is the case for only GPS, but the good L2 
    lsp['freqs'] = [1, 20, 5]
    if allfreq is True:
        # 307 was making it crash.  did not check as to why
        # includes glonass, galileo, and beidou
        lsp['freqs'] = [1, 20, 5, 101, 102, 201, 205, 206, 207, 208, 302, 306]

    if l1 is True:
        lsp['freqs'] = [1]

    if l2c is True:
        lsp['freqs'] = [20]

    if len(frlist) == 0:
        print('Using standard frequency choices.')
    else:
        print('Implementing user-provided frequency list.')
        lsp['freqs'] = frlist

    # create a list with all values equal to reqA
    # but the length of the list depends on the length of the list of frequencies
    lsp['reqAmp'] = [reqA]*len(lsp['freqs'])

    lsp['refraction'] = refraction

    # write new RH results  each time you run the code
    lsp['overwriteResults'] = True

    # if snr file does not exist, try to make one
    lsp['seekRinex'] = False

    # compress snr files after analysis - saves disk space
    lsp['wantCompression'] = False

    # periodogram plots come to the screen
    lsp['plt_screen'] = False

    # command line req to only do a single satellite - default is do all satellites
    lsp['onesat'] = None

    # default will now be False ....
    # send some information on periodogram RH retrievals to the screen
    lsp['screenstats'] = False

    # save the output plots
    lsp['pltname'] = station + '_lsp.png'

    # how long can the arc be, in minutes
    lsp['delTmax'] = delTmax  
 
    # gzip SNR files after running the code
    lsp['gzip'] = False   

    print('writing out to:', outputfile)
    with open(outputfile, 'w+') as outfile:
        json.dump(lsp, outfile, indent=4)


def main():
    args = parse_arguments()
    make_gnssir_input(**args)


if __name__ == "__main__":
    main()