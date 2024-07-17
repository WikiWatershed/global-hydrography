from pandas import DataFrame
import requests

GEOGLOW_TDX_HEADER_URL = "https://geoglows-v2.s3-us-west-2.amazonaws.com/tdxhydro-processing/tdx_header_numbers.json"


class TDXPreprocessor:

    __tdx_header_crosswalk = None

    @property
    def tdx_header_crosswalk(self) -> dict[int, int]:
        """Getter method for tdx header lookup dictionary

        Returns:
            Dict[int, int]:
                A dictionary with keys being the 10-digit TDX-Hydro basin ID number
                and values being the geoglows TDH header value (used to global conversion)

        """
        # if already initialized return the cached copy
        if self.__tdx_header_crosswalk is not None:
            return self.__tdx_header_crosswalk

        response = requests.get(GEOGLOW_TDX_HEADER_URL)
        self.__tdx_header_crosswalk = {
            int(k): int(v) for k, v in response.json().items()
        }
        return self.__tdx_header_crosswalk

    def tdx_to_global_linkno(
        self,
        df: DataFrame,
        tdx_hydro_region: int,
    ) -> DataFrame:
        """Transforms LINKNOs fields of TDXHydroRegion dataset into a globally unique LINKNOs

        This includes the LINKNO field but also the upstream and downstream links

        This operation is based off Geoglows V2 approach using the following equation.
        `LINKNO_NEW = LINKNO_OLD + (TDX_HEADER_NUMBER * 10_000_000)`

        WHERE:
            LINKNO_OLD: is the native LINKNO field provided in the TDX Hydro dataset
            TDX_HEADER_NUMBER: is the header value obtained from comparing the TDX_Hydro_ID (a 10 digit numerical value)
                to the Geoglows headers crosswalk provided here.
                https://geoglows-v2.s3-us-west-2.amazonaws.com/tdxhydro-processing/tdx_header_numbers.json

        Parameters:
            df: DataFrame
                A pandas.DataFrame or geopandas.GeoDataFrame object.
            tdx_hydro_region: int
                The 10-digit integer id of the TDX Hydro dataset used in filenames
                and corresponding to HydroBasins Level 2 codes.

        Return:
            DataFrame:
                A DataFrame or GeoDataFrame with the appropriate globally unique conversions applied to to linkid fields.


        """

        fields = [
            "LINKNO", "DSLINKNO", "USLINKNO1", "USLINKNO2", # For streamnet files
            'streamID', # For basins files. Identical to "LINKNO".
        ]

        # Only use fields if in df
        fields_to_use = []
        for field in fields:
            if any(df.columns.isin([field])):
                fields_to_use.append(field)

        header_id = int(self.tdx_header_crosswalk[tdx_hydro_region])
        for field in fields_to_use:
            # note that fields with -1 indicate no link and we do not
            # want to transform those, which is why we have this loc statement
            df.loc[df[field] > -1, field] += header_id * 10_000_000
        return df


    def tdx_drop_useless_columns(
        self,
        df: DataFrame,
    ) -> DataFrame:
        """Drops columns that are of no use.
        See `sandbox/explore_data_sources.ipynb`

        Parameters:
            df: DataFrame
                A pandas.DataFrame or geopandas.GeoDataFrame object.

        Return:
            DataFrame:
                A DataFrame or GeoDataFrame without useless fields.
        """

        useless_columns = [
            'WSNO', # identical values to 'LINKNO'
            'DSNODEID', # all -1
        ]

        # Only drop if in df
        columns_to_drop = []
        for column in useless_columns:
            if any(df.columns.isin([column])):
                columns_to_drop.append(column)

        return df.drop(columns=columns_to_drop, inplace=True)
