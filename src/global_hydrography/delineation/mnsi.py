from pandas import DataFrame, Series

# The algorithm was developed back on the information provided in this paper
# https://doi.org/10.1016/j.envsoft.2017.06.009

# provide the DataFrame fields as constants that can be
# updates if field names every change
LINK = "LINKNO"
US_LEFT = "USLINKNO1"
US_RIGHT = "USLINKNO2"
DS_LINK = "DSLINKNO"

# These are the set of output fields
# If you change these be sure to also update the documentation!
DISCOVER = "DISCOVER_TIME"
FINISH = "FINISH_TIME"
ROOT = "ROOT_ID"


def modified_nest_set_index(df: DataFrame) -> DataFrame:
    """Computes the modified next set index for root nodes in DataFrame

    Adds three (3) additional fields to the DataFrame to store the
    modified nested set index information.

        DISCOVER_TIME: int
            The time (number of steps) it took for the algorithm to first visit this reach.
        FINISH_TIME: int
            The time (number of steps) it took for the algorithm to revisit this reach.
        ROOT_ID: int
            The id of the root node of the graph with reach belongs to.
            The values for DISCOVER_TIME and FINISH_TIME are not globally unique,
            but rather unique for a given watershed. ROOT_ID allows for the reaches
            that may share common DISCOVER_TIME and FINISH_TIME values to differentiate.

    Parameters:
        df: DataFrame
            A DataFrame object loading from a TDX Hydro datasource
    Returns:
        DataFrame:
            DataFrame instance containing additional fields with modified
            nested set index information.

    """

    # Add additional columns to hold the output of modified nested set index algorithm
    df[DISCOVER] = None
    df[FINISH] = None
    df[ROOT] = None

    # identify all the root nodes in the DataFrame
    roots = df.loc[df[DS_LINK] == -1, LINK]

    # ensure linkno is the index so that when we export the
    # Dataframe linkno is the key of the dictionary
    df = df.set_index(LINK)
    nodes = df.to_dict(orient="index")

    # helper function to compute the modified nested set index for a given graph
    def __compute_index_for_root(root: Series):
        clock = 1
        left_to_process = [root]

        while left_to_process:
            node_id = left_to_process.pop()
            node = nodes[node_id]

            # if this is the first time we have visited this node
            if not node[DISCOVER]:
                # id this node as part of this tree
                node[ROOT] = root
                # set discovery time
                node[DISCOVER] = clock

                # we need to revisit this node to set finish time
                # so add back to stack but before pushing upstream
                # so that is will be processed after upstream nodes are
                left_to_process.append(node_id)

                # move up the tree
                if df.loc[node_id, US_LEFT] != -1:  # if not leaf
                    left_to_process.append(node[US_LEFT])
                if df.loc[node_id, US_RIGHT] != -1:  # if not leaf
                    left_to_process.append(node[US_RIGHT])
                clock += 1

            elif not node[FINISH]:
                node[FINISH] = clock

    # run the modified nest set index algorithm
    for root in roots:
        __compute_index_for_root(root)

    # map the MNSI information back to the original DataFrame
    df_msni = DataFrame(nodes)
    df_msni = df_msni.transpose()
    for f in (ROOT, DISCOVER, FINISH):
        df[f] = df_msni[f].astype('int32')
    df = df.reset_index()

    return df
