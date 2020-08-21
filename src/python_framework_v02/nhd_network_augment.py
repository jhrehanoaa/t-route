import nhd_network

def network_connections(data, network_data):
    
    """
    Extract upstream and downstream connections between segments in network

    Args:
        data (DataFrame): Network parameter dataset, prepared
        network_data (dict): network metadata

    Returns:
        conn (dict): downstream connections
        rconn (dict): upstream connections 

    """
    
    # extract downstream connections
    conn = nhd_network.extract_connections(data, network_data["downstream_col"])
    
    # extract upstream connections
    rconn = nhd_network.reverse_network(conn)
    
    return conn, rconn

def headwater_connections(data, network_data):

    """
    Determine which segments are and are not headwaters. 
    Headwaters are defined as segments with no upstream connection, only downstream connections. 
    Non-headwaters are defined as segments with both upstream and downstream connections. 

    Args:
        data (DataFrame): Network parameter dataset, prepared

    Returns:
        hw_conn (dict): downstream connections, headwaters only
        non_hw_conn (dict): downstream connections, non headwaters only

    """

    # extract network connections
    conn, rconn = network_connections(data, network_data)
    
    hw = []  # store headwater segments
    non_hw = []  # store non-headwater segments

    for seg in rconn.keys():
        # if there is no upstream connection anda downstream connection, it is a headwater
        if bool(rconn[seg]) == False and bool(conn[seg]) == True:
            hw.append(seg)

        # if there is an upstream connection and a downstream connection, it is a non-headwater (midwater?)
        elif bool(rconn[seg]) == True and bool(conn[seg]) == True:
            non_hw.append(seg)

    # get segment key-value pairs from the connections dictionary
    hw_conn = {key: conn[key] for key in hw}
    non_hw_conn = {key: conn[key] for key in non_hw}

    return hw_conn, non_hw_conn