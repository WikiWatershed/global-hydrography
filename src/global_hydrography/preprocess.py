from geopandas import GeoDataFrame
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
        df: GeoDataFrame,
        tdx_id: int,
    ) -> GeoDataFrame:
        """Transforms LINKNOs fields of TDXHydro dataset into a globally unique LINKNOs

        This includes the LINKNO field but also the upstream and downstream links

        This operation is based off Geoglows V2 approach using the following equation.
        `LINKNO_NEW = LINKNO_OLD + (TDX_HEADER_NUMBER * 10_000_000)`

        WHERE:
            LINKNO_OLD: is the native LINKNO field provided in the TDX Hydro dataset
            TDX_HEADER_NUMBER: is the header value obtained from comparing the TDX_Hydro_ID (a 10 digit numerical value)
                to the Geoglows headers crosswalk provided here.
                https://geoglows-v2.s3-us-west-2.amazonaws.com/tdxhydro-processing/tdx_header_numbers.json

        Parameters:
            df: GeoDataFrame
                A geopandas.GeoDataFrame object.
            tdx_header_id: int
                The integer id of the TDX hydro dataset

        Return:
            GeoDataFrame:
                A GeoDataFrame with the appropriate globally unique conversions applied to to linkid fields.


        """

        fields = ["LINKNO", "DSLINKNO", "USLINKNO1", "USLINKNO2"]

        header_id = int(self.tdx_header_crosswalk[tdx_id])
        for field in fields:
            # note that fields with -1 indicate no link and we do not
            # want to transform those, which is why we have this loc statement
            df.loc[df[field] > -1, field] += header_id * 10_000_000
        return df


    def tdx_drop_useless_columns(
        self,
        df: GeoDataFrame,
    ) -> GeoDataFrame:
        """Drops columns that are of no use.
        See `sandbox/explore_data_sources.ipynb`

        Parameters:
            df: GeoDataFrame
                A geopandas.GeoDataFrame object.

        Return:
            GeoDataFrame:
                A GeoDataFrame without useless fields.
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
