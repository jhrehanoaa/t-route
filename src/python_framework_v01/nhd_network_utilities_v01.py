import networkbuilder as networkbuilder
import os
import traceback
import geopandas as gpd
import pandas as pd
import zipfile
import xarray as xr
import network_dl
import json


def get_geo_file_table_rows(
    geo_file_path=None,
    data_link=None,
    layer_string=None,
    driver_string=None,
    verbose=False,
    debuglevel=0,
):

    if not os.path.exists(geo_file_path):
        filename = os.path.basename(geo_file_path)
        msg = ""
        msg = msg + f"\nTarget input file not found on file system here:"
        msg = msg + f"\n{geo_file_path}"
        msg = msg + f"\n"
        msg = msg + f"\nThis routine will attempt to download the file from here:"
        msg = msg + f"\n{data_link}"
        msg = (
            msg
            + f"\nYou should not need to repeat this step once the file is downloaded."
        )
        msg = msg + f"\n"
        msg = (
            msg
            + f"\nIf you wish to manually download the file (and compress it), please use the following commands:"
        )
        msg = msg + f'\n# export ROUTELINK="{filename}"'
        msg = (
            msg
            + f"\n# wget -c https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nwm.v2.0.3/parm/domain/$ROUTELINK"
        )
        msg = (
            msg
            + f"\n# export $ROUTELINK_UNCOMPRESSED=${{ROUTELINK/\.nc/_uncompressed.nc}}"
        )
        msg = msg + f"\n# mv $ROUTELINK $ROUTELINK_UNCOMPRESSED"
        msg = msg + f"\n# nccopy -d1 -s $ROUTELINK_UNCOMPRESSED $ROUTELINK"

        """
        Full CONUS route-link file not found on file system.
        This routine will attempt to download the file. 

        If you wish to manually download the file, please use the following commands:

        > export ROUTELINK="RouteLink_NHDPLUS.nc"
        > wget -c https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nwm.v2.0.3/parm/domain/$ROUTELINK
        > nccopy -d1 -s $ROUTELINK ${ROUTELINK/\.nc/_compressed.nc}
        """
        print(msg)

        network_dl.download(geo_file_path, data_link)

    # NOTE: these methods can lose the "connections" and "rows" arguments when
    # implemented as class methods where those arrays are members of the class.
    # TODO: Improve the error handling here for a corrupt input file

    if debuglevel <= -1:
        print(
            f"reading -- dataset: {geo_file_path}; layer: {layer_string}; driver: {driver_string}"
        )
    if driver_string == "NetCDF":  # Use Xarray to read a netcdf table
        try:
            geo_file = xr.open_dataset(geo_file_path)
            geo_keys = geo_file.data_vars.keys()
            geo_keys = list(geo_keys)
            geo_file_rows = (geo_file.to_dataframe()).values
        except Exception as e:
            print(e)
            if debuglevel <= -1:
                traceback.print_exc()
        # The xarray method for NetCDFs was implemented after the geopandas method for
        # GIS source files. It's possible (probable?) that we are doing something
        # inefficient by converting away from the Pandas dataframe.
        # TODO: Check the optimal use of the Pandas dataframe
    elif driver_string == "csv":  # Use Pandas to read zipped csv/txt
        try:
            HEADER = None  # TODO: standardize the mask format or add some logic to handle headers or other variations in format
            geo_file = pd.read_csv(geo_file_path, header=HEADER)
            geo_keys = []
        except Exception as e:
            print(e)
            if debuglevel <= -1:
                traceback.print_exc()
        geo_file_rows = geo_file.to_numpy()
    elif driver_string == "zip":  # Use Pandas to read zipped csv/txt
        try:
            with zipfile.ZipFile(geo_file_path, "r") as zcsv:
                with zcsv.open(layer_string) as csv:
                    geo_file = pd.read_csv(csv)
            geo_keys = []
        except Exception as e:
            print(e)
            if debuglevel <= -1:
                traceback.print_exc()
        geo_file_rows = geo_file.to_numpy()
    else:  # Read Shapefiles, Geodatabases with Geopandas/fiona
        try:
            geo_file = gpd.read_file(
                geo_file_path, driver=driver_string, layer=layer_string
            )
            geo_keys = geo_file.keys().tolist()
            geo_file_rows = geo_file.to_numpy()
        except Exception as e:
            print(e)
            if debuglevel <= -1:
                traceback.print_exc()
        if debuglevel <= -2:
            try:
                geo_file.plot()
            except Exception as e:
                print(r"cannot plot geofile (not necessarily a problem)")
                traceback.print_exc()
    if debuglevel <= -1:
        # official docs here:
        # https://pandas.pydata.org/docs/user_guide/options.html
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_colwidth", -1)
        print(geo_file.head())  # Preview the first 5 lines of the loaded data

    return geo_file_rows, geo_keys


# TODO: Give this function a more appropriate general name (it does more that build connections)
def build_connections_object(
    geo_file_rows=None,
    mask_set=None,
    key_col=None,
    downstream_col=None,
    length_col=None,
    terminal_code=None,
    waterbody_col=None,
    waterbody_null_code=None,
    verbose=False,
    debuglevel=0,
):
    (connections) = networkbuilder.get_down_connections(
        rows=geo_file_rows,
        mask_set=mask_set,
        key_col=key_col,
        downstream_col=downstream_col,
        length_col=length_col,
        verbose=verbose,
        debuglevel=debuglevel,
    )

    (
        all_keys,
        ref_keys,
        headwater_keys,
        terminal_keys,
        terminal_ref_keys,
        circular_keys,
    ) = networkbuilder.determine_keys(
        connections=connections
        # , key_col = key_col
        # , downstream_col = downstream_col
        ,
        terminal_code=terminal_code,
        verbose=verbose,
        debuglevel=debuglevel,
    )

    (
        junction_keys,
        confluence_segment_set,
        visited_keys,
        visited_terminal_keys,
        junction_count,
    ) = networkbuilder.get_up_connections(
        connections=connections,
        terminal_code=terminal_code,
        headwater_keys=headwater_keys,
        terminal_keys=terminal_keys,
        verbose=verbose,
        debuglevel=debuglevel,
    )

    waterbody_dict = None
    waterbody_segments = None
    waterbody_outlet_set = None
    waterbody_upstreams_set = None
    waterbody_downstream_set = None

    # TODO: Set/pass/identify a proper flag value
    if waterbody_col is not None:
        (
            waterbody_dict,
            waterbody_segments,
            waterbody_outlet_set,
            waterbody_upstreams_set,
            waterbody_downstream_set,
        ) = networkbuilder.get_waterbody_segments(
            connections=connections,
            terminal_code=terminal_code,
            waterbody_col=waterbody_col,
            waterbody_null_code=waterbody_null_code,
            verbose=verbose,
            debuglevel=debuglevel
            # , debuglevel = -3
        )

    # TODO: change names to reflect type set or dict
    return (
        connections,
        all_keys,
        ref_keys,
        headwater_keys,
        terminal_keys,
        terminal_ref_keys,
        circular_keys,
        junction_keys,
        visited_keys,
        visited_terminal_keys,
        junction_count,
        confluence_segment_set,
        waterbody_dict,
        waterbody_segments,
        waterbody_outlet_set,
        waterbody_upstreams_set,
        waterbody_downstream_set,
    )


def convert_text_cols_to_val(
    geo_keys,
    key_col,
    downstream_col,
    length_col,
    waterbody_col,
    verbose=False,
    debuglevel=0,
):
    """This function is now deprecated with 
    the preferred path being to simply transition to 
    use of a dataframe with column keys to refer to 
    data columns."""

    key_col = geo_keys.index(key_col) + 2
    downstream_col = geo_keys.index(downstream_col) + 2
    length_col = geo_keys.index(length_col) + 2
    waterbody_col = geo_keys.index(waterbody_col) + 2

    return (
        key_col,
        downstream_col,
        length_col,
        waterbody_col,
    )


def do_connections(
    geo_file_path=None,
    data_link=None,
    cols_as_text=False,
    title_string=None,
    layer_string=None,
    driver_string=None,
    key_col=None,
    downstream_col=None,
    length_col=None,
    terminal_code=None,
    waterbody_col=None,
    waterbody_null_code=None,
    mask_file_path=None,
    mask_driver_string=None,
    mask_layer_string=None,
    mask_key_col=None,
    verbose=False,
    debuglevel=0,
):

    if verbose:
        print(title_string)
    geo_file_rows, geo_keys = get_geo_file_table_rows(
        geo_file_path=geo_file_path,
        data_link=data_link,
        layer_string=layer_string,
        driver_string=driver_string,
        verbose=verbose,
        debuglevel=debuglevel,
    )

    if cols_as_text:
        (
            key_col,
            downstream_col,
            length_col,
            waterbody_col,
        ) = convert_text_cols_to_val(
            geo_keys,
            key_col,
            downstream_col,
            length_col,
            waterbody_col,
            verbose,
            debuglevel,
        )

    if debuglevel <= -1:
        print(f"MASK: {mask_file_path}")
    if mask_file_path:
        mask_file_rows, _ = get_geo_file_table_rows(
            geo_file_path=mask_file_path,
            layer_string=mask_layer_string,
            driver_string=mask_driver_string,
            verbose=verbose,
            debuglevel=debuglevel,
        )
        # TODO: make mask dict with additional attributes, e.g., names
        mask_set = {row[mask_key_col] for row in mask_file_rows}
    else:
        mask_set = {row[key_col] for row in geo_file_rows}

    return build_connections_object(
        geo_file_rows=geo_file_rows,
        mask_set=mask_set,
        key_col=key_col,
        downstream_col=downstream_col,
        length_col=length_col,
        terminal_code=terminal_code,
        waterbody_col=waterbody_col,
        waterbody_null_code=waterbody_null_code,
        verbose=verbose,
        debuglevel=debuglevel,
    )

    # return connections, all_keys, ref_keys, headwater_keys \
    #     , terminal_keys, terminal_ref_keys \
    #     , circular_keys, junction_keys \
    #     , visited_keys, visited_terminal_keys \
    #     , junction_count


def get_nhd_connections(supernetwork_parameters={}, verbose=False, debuglevel=0):
    # TODO: convert to get.
    # as in: text=supernetwork_parameters.get("cols_as_text",None):
    # Will need to check if something depends on the None elsewhere.
    if "waterbody_col" not in supernetwork_parameters:
        supernetwork_parameters.update({"waterbody_col": None})
        supernetwork_parameters.update({"waterbody_null_code": None})

    if "mask_file_path" not in supernetwork_parameters:
        # TODO: doing things this way may mean we are reading the same file twice -- fix this [maybe] by implementing an overloaded return
        supernetwork_parameters.update({"mask_file_path": None})
        supernetwork_parameters.update({"mask_layer_string": None})
        supernetwork_parameters.update({"mask_driver_string": None})
        supernetwork_parameters.update({"mask_key_col": None})

    if "data_link" not in supernetwork_parameters:
        supernetwork_parameters.update({"data_link": None})

    return do_connections(
        geo_file_path=supernetwork_parameters["geo_file_path"],
        data_link=supernetwork_parameters["data_link"],
        cols_as_text=supernetwork_parameters.get("cols_as_text", None),
        key_col=supernetwork_parameters["key_col"],
        downstream_col=supernetwork_parameters["downstream_col"],
        length_col=supernetwork_parameters["length_col"],
        terminal_code=supernetwork_parameters["terminal_code"],
        waterbody_col=supernetwork_parameters["waterbody_col"],
        waterbody_null_code=supernetwork_parameters["waterbody_null_code"],
        title_string=supernetwork_parameters["title_string"],
        driver_string=supernetwork_parameters["driver_string"],
        layer_string=supernetwork_parameters["layer_string"],
        mask_file_path=supernetwork_parameters["mask_file_path"],
        mask_layer_string=supernetwork_parameters["mask_layer_string"],
        mask_driver_string=supernetwork_parameters["mask_driver_string"],
        mask_key_col=supernetwork_parameters["mask_key_col"],
        debuglevel=debuglevel,
        verbose=verbose,
    )


def set_waterbody_parameters(
    supernetwork="", geo_input_folder=None, verbose=True, debuglevel=0
):
    """ Provide the waterbody parameters for the built-in cases """
    if supernetwork == "Pocono_TEST1":
        return {
            "level_pool": {
                "level_pool_waterbody_parameter_file_path": os.path.join(
                    geo_input_folder, "NWM_2.1_Sample_Datasets", "LAKEPARM_POCONO.nc"
                ),
                "level_pool_waterbody_id": "lake_id",
                "level_pool_waterbody_area": "LkArea",  # area of reservoir
                "level_pool_weir_elevation": "WeirE",
                "level_pool_waterbody_max_elevation": "LkMxE",
                "level_pool_outfall_weir_coefficient": "WeirC",
                "level_pool_outfall_weir_length": "WeirL",
                "level_pool_overall_dam_length": "DamL",
                "level_pool_orifice_elevation": "OrificeE",
                "level_pool_orifice_coefficient": "OrificeC",
                "level_pool_orifice_area": "OrificeA",
            },
        }
    else:
        return {
            "level_pool": {
                "level_pool_waterbody_parameter_file_path": os.path.join(
                    geo_input_folder, "NWM_2.1_Sample_Datasets", "LAKEPARM_CONUS.nc"
                ),
                "level_pool_waterbody_id": "lake_id",
                "level_pool_waterbody_area": "LkArea",  # area of reservoir
                "level_pool_weir_elevation": "WeirE",
                "level_pool_waterbody_max_elevation": "LkMxE",
                "level_pool_outfall_weir_coefficient": "WeirC",
                "level_pool_outfall_weir_length": "WeirL",
                "level_pool_overall_dam_length": "DamL",
                "level_pool_orifice_elevation": "OrificeE",
                "level_pool_orifice_coefficient": "OrificeC",
                "level_pool_orifice_area": "OrificeA",
            },
        }


def set_supernetwork_parameters(
    supernetwork="", geo_input_folder=None, verbose=True, debuglevel=0
):
    """ Provide the supernetwork parameters for the built-in cases """

    # The following datasets are extracts from the feature datasets available
    # from https://www.nohrsc.noaa.gov/pub/staff/keicher/NWM_live/web/data_tools/
    # the CONUS_ge5 and Brazos_LowerColorado_ge5 datasets are included
    # in the github test folder

    supernetwork_options = {
        "Pocono_TEST1",
        "Pocono_TEST2",
        "LowerColorado_Conchos_FULL_RES",
        "Brazos_LowerColorado_ge5",
        "Brazos_LowerColorado_FULL_RES",
        "Brazos_LowerColorado_Named_Streams",
        "CONUS_ge5",
        "Mainstems_CONUS",
        "CONUS_Named_Streams",
        "CONUS_FULL_RES_v20",
        "custom",
    }
    if supernetwork not in supernetwork_options:
        print(
            "Note: please call function with supernetworks set to one of the following:"
        )
        for s in supernetwork_options:
            print(f"'{s}'")
        exit()
    elif supernetwork == "Pocono_TEST1":
        return {
            "geo_file_path": os.path.join(
                geo_input_folder, r"PoconoSampleData1", r"PoconoSampleRouteLink1.shp"
            ),
            "key_col": 18,
            "downstream_col": 23,
            "length_col": 5,
            "manningn_col": 20,
            "manningncc_col": 21,
            "slope_col": 10,
            "bottomwidth_col": 2,
            "topwidth_col": 11,
            "topwidthcc_col": 12,
            "waterbody_col": 8,
            "waterbody_null_code": -9999,
            "MusK_col": 7,
            "MusX_col": 8,
            "ChSlp_col": 12,
            "terminal_code": 0,
            "title_string": "Pocono Test Example",
            "driver_string": "ESRI Shapefile",
            "layer_string": 0,
        }

    elif supernetwork == "Pocono_TEST2":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "Pocono Test 2 Example",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder,
                    r"Channels",
                    r"masks",
                    r"PoconoRouteLink_TEST2_nwm_mc.txt",
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

        # return {
        #'geo_file_path' : os.path.join(geo_input_folder
    # , r'PoconoSampleData2'
    # , r'PoconoRouteLink_testsamp1_nwm_mc.shp')
    # , 'key_col' : 18
    # , 'downstream_col' : 23
    # , 'length_col' : 5
    # , 'manningn_col' : 20
    # , 'manningncc_col' : 21
    # , 'slope_col' : 10
    # , 'bottomwidth_col' : 2
    # , 'topwidth_col' : 11
    # , 'topwidthcc_col' : 12
    # , 'MusK_col' : 6
    # , 'MusX_col' : 7
    # , 'ChSlp_col' : 3
    # , 'terminal_code' : 0
    # , 'title_string' : 'Pocono Test 2 Example'
    # , 'driver_string' : 'ESRI Shapefile'
    # , 'layer_string' : 0
    # }

    elif supernetwork == "LowerColorado_Conchos_FULL_RES":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "NHD 2.0 Conchos Basin of the LowerColorado River",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder,
                    r"Channels",
                    r"masks",
                    r"LowerColorado_Conchos_FULL_RES.txt",
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

    elif supernetwork == "Brazos_LowerColorado_ge5":
        return {
            "geo_file_path": os.path.join(
                geo_input_folder, r"Channels", r"NHD_BrazosLowerColorado_Channels.shp"
            ),
            "key_col": 2,
            "downstream_col": 7,
            "length_col": 6,
            "manningn_col": 11,
            "slope_col": 10,
            "bottomwidth_col": 12,
            "MusK_col": 7,
            "MusX_col": 8,
            "ChSlp_col": 13,
            "terminal_code": 0,
            "title_string": "NHD Subset including Brazos + Lower Colorado\nNHD stream orders 5 and greater",
            "driver_string": "ESRI Shapefile",
            "layer_string": 0,
        }

    elif supernetwork == "Brazos_LowerColorado_FULL_RES":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "NHD 2.0 Brazos and LowerColorado Basins",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder,
                    r"Channels",
                    r"masks",
                    r"Brazos_LowerColorado_FULL_RES.txt",
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

    elif supernetwork == "Brazos_LowerColorado_Named_Streams":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "NHD 2.0 GNIS labeled streams in the Brazos and LowerColorado Basins",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder,
                    r"Channels",
                    r"masks",
                    r"Brazos_LowerColorado_Named_Streams.csv",
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

    elif supernetwork == "CONUS_ge5":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "NHD CONUS Order 5 and Greater",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder, r"Channels", r"masks", r"CONUS_ge5.txt"
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

    elif supernetwork == "Mainstems_CONUS":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "CONUS 'Mainstems' (Channels below gages and AHPS prediction points)",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder, r"Channels", r"masks", r"conus_Mainstem_links.txt"
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

        # return {
        #     "geo_file_path": os.path.join(
        #         geo_input_folder, r"Channels", r"conus_routeLink_subset.nc"
        #     ),
        #     "key_col": 0,
        #     "downstream_col": 2,
        #     "length_col": 10,
        #     "manningn_col": 11,
        #     "manningncc_col": 20,
        #     "slope_col": 12,
        #     "bottomwidth_col": 14,
        #     "topwidth_col": 22,
        #     "topwidthcc_col": 21,
        #     "waterbody_col": 15,
        #     "waterbody_null_code": -9999,
        #     "MusK_col": 8,
        #     "MusX_col": 9,
        #     "ChSlp_col": 13,
        #     "terminal_code": 0,
        #     "title_string": 'CONUS "Mainstem"',
        #     "driver_string": "NetCDF",
        #     "layer_string": 0,
        # }

    elif supernetwork == "CONUS_Named_Streams":
        dict = set_supernetwork_parameters(
            supernetwork="CONUS_FULL_RES_v20", geo_input_folder=geo_input_folder
        )
        dict.update(
            {
                "title_string": "CONUS NWM v2.0 only GNIS labeled streams",  # overwrites other title...
                "mask_file_path": os.path.join(
                    geo_input_folder,
                    r"Channels",
                    r"masks",
                    r"nwm_reaches_conus_v21_wgnis_name.csv",
                ),
                "mask_driver_string": r"csv",
                "mask_layer_string": r"",
                "mask_key_col": 0,
                "mask_name_col": 1,  # TODO: Not used yet.
            }
        )
        return dict

    elif supernetwork == "CONUS_FULL_RES_v20":

        ROUTELINK = r"RouteLink_NHDPLUS"
        ModelVer = r"nwm.v2.0.3"
        ext = r"nc"
        sep = r"."

        return {
            "geo_file_path": os.path.join(
                geo_input_folder, r"Channels", sep.join([ROUTELINK, ModelVer, ext])
            ),
            "data_link": f"https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/{ModelVer}/parm/domain/{ROUTELINK}{sep}{ext}",
            "key_col": 0,
            "downstream_col": 2,
            "length_col": 10,
            "manningn_col": 11,
            "manningncc_col": 20,
            "slope_col": 12,
            "bottomwidth_col": 14,
            "topwidth_col": 22,
            "topwidthcc_col": 21,
            "waterbody_col": 15,
            "waterbody_null_code": -9999,
            "MusK_col": 8,
            "MusX_col": 9,
            "ChSlp_col": 13,
            "terminal_code": 0,
            "title_string": "CONUS Full Resolution NWM v2.0",
            "driver_string": "NetCDF",
            "layer_string": 0,
            "waterbody_parameter_file_type": "Level_Pool",
        }


def read_custom_input_json(custom_input_file):
    with open(custom_input_file) as json_file:
        data = json.load(json_file)
        supernetwork_parameters = data.get("supernetwork_parameters", None)
        waterbody_parameters = data.get("waterbody_parameters", {})
        forcing_parameters = data.get("forcing_parameters", {})
        restart_parameters = data.get("restart_parameters", {})
        output_parameters = data.get("output_parameters", {})
        run_parameters = data.get("run_parameters", {})
        # TODO: add error trapping for potentially missing files
    return (
        supernetwork_parameters,
        waterbody_parameters,
        forcing_parameters,
        restart_parameters,
        output_parameters,
        run_parameters,
    )


# TODO: confirm that this function is not used, and if so, consider removing it
def set_networks(supernetwork="", geo_input_folder=None, verbose=True, debuglevel=0):

    supernetwork_parameters = set_supernetwork_parameters(
        supernetwork=supernetwork, geo_input_folder=geo_input_folder
    )
    supernetwork_values = get_nhd_connections(
        supernetwork_parameters=supernetwork_parameters,
        verbose=verbose,
        debuglevel=debuglevel,
    )
    return supernetwork_parameters, supernetwork_values


def read_waterbody_df(waterbody_parameters, waterbodies_values, wbtype="level_pool"):
    if wbtype == "level_pool":
        wb_params = waterbody_parameters[wbtype]
        return read_level_pool_waterbody_df(
            wb_params["level_pool_waterbody_parameter_file_path"],
            wb_params["level_pool_waterbody_id"],
            waterbodies_values[wbtype],
        )


def read_level_pool_waterbody_df(
    parm_file, lake_index_field="lake_id", lake_id_mask=None
):

    ds = xr.open_dataset(parm_file)
    df1 = ds.to_dataframe().set_index(lake_index_field)
    if lake_id_mask:
        df1 = df1.loc[lake_id_mask, :]
    return df1


def get_ql_from_wrf_hydro(qlat_files, index_col="station_id", value_col="q_lateral"):
    li = []

    for filename in qlat_files:
        ds = xr.open_dataset(filename)
        df1 = ds.to_dataframe()

        li.append(df1)

    frame = pd.concat(li, axis=0, ignore_index=False)
    mod = frame.reset_index()
    ql = mod.pivot(index=index_col, columns="time", values=value_col)

    return ql


def get_stream_restart_from_wrf_hydro(
    channel_initial_states_file,
    crosswalk_file,
    channel_ID_column,
    us_flow_column="qlink1",
    ds_flow_column="qlink2",
    depth_column="hlink",
    default_us_flow_column="qu0",
    default_ds_flow_column="qd0",
    default_depth_column="h0",
):
    """
    channel_initial_states_file: WRF-HYDRO standard restart file
    us_flow_column: column in the restart file to use for upstream flow initial state
    ds_flow_column: column in the restart file to use for downstream flow initial state
    depth_column: column in the restart file to use for depth initial state
    crosswalk_file: File containing channel IDs IN THE ORDER of the Restart File
    channel_ID_column: field in the crosswalk file to assign as the index of the restart values
    """

    xds = xr.open_dataset(crosswalk_file)
    xdf = xds[channel_ID_column].to_dataframe()
    xdf = xdf.reset_index()
    xdf = xdf[[channel_ID_column]]
    qds = xr.open_dataset(channel_initial_states_file)
    if depth_column in qds:
        qdf2 = qds[[us_flow_column, ds_flow_column, depth_column]].to_dataframe()
    else:
        qdf2 = qds[[us_flow_column, ds_flow_column]].to_dataframe()
        qdf2[depth_column] = 0
    qdf2 = qdf2.reset_index()
    qdf2 = qdf2[[us_flow_column, ds_flow_column, depth_column]]
    qdf2.rename(
        columns={
            us_flow_column: default_us_flow_column,
            ds_flow_column: default_ds_flow_column,
            depth_column: default_depth_column,
        },
        inplace=True,
    )
    qdf2[channel_ID_column] = xdf
    qdf2 = qdf2.reset_index().set_index([channel_ID_column])

    q_initial_states = qdf2

    return q_initial_states


def get_reservoir_restart_from_wrf_hydro(
    waterbody_intial_states_file,
    crosswalk_file,
    waterbody_ID_field,
    crosswalk_filter_file,
    crosswalk_filter_file_field,
    crosswalk_file_xs_field="links",
    crosswalk_file_xs_value=0,
    waterbody_flow_column="qlakeo",
    waterbody_depth_column="resht",
    default_waterbody_flow_column="qd0",
    default_waterbody_depth_column="h0",
):
    # TODO: Instead of using a filter file, just use the set of waterbodies.
    xds = xr.open_dataset(crosswalk_file)
    X = xds[waterbody_ID_field]

    if crosswalk_filter_file:
        fds = xr.open_dataset(crosswalk_filter_file)
        xdf = X.loc[X.isin(fds[crosswalk_filter_file_field])].to_dataframe()
    else:
        xdf = X.to_dataframe()

    xdf = xdf.reset_index()[waterbody_ID_field]

    # read initial states from r&r output
    resds = xr.open_dataset(waterbody_intial_states_file)
    resdf = resds[[waterbody_flow_column, waterbody_depth_column]].to_dataframe()
    resdf = resdf.reset_index()
    resdf = resdf[[waterbody_flow_column, waterbody_depth_column]]
    resdf.rename(
        columns={
            waterbody_flow_column: default_waterbody_flow_column,
            waterbody_depth_column: default_waterbody_depth_column,
        },
        inplace=True,
    )

    mod = resdf.join(xdf).reset_index().set_index(waterbody_ID_field)
    init_waterbody_states = mod

    return init_waterbody_states
