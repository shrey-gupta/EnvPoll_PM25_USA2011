import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans

def _cluster_coords(coordinates: pd.DataFrame, method: str, n_clusters: int):
    if "x" not in coordinates.columns:
        raise Exception("'x' must be in the input coordinate columns.")
    if "y" not in coordinates.columns:
        raise Exception("'y' must be in the input coordinate columns.")
    if method not in ["GaussianMixture", "KMeans"]:
        raise Exception("Inappropriate method.")

    np.random.seed(1000)
    unique_coors = coordinates.drop_duplicates()
    if method == 'GaussianMixture':
        cluster_model = GaussianMixture(n_components=n_clusters).fit(unique_coors)
    elif method == "KMeans":
        cluster_model = KMeans(n_clusters=n_clusters).fit(unique_coors)
    coor_pred = cluster_model.predict(unique_coors)
    whole_pred = cluster_model.predict(coordinates)
    coor_clusters = unique_coors.copy()
    coor_clusters["cluster id"] = coor_pred
    whole_df = pd.DataFrame(whole_pred, index=coordinates.index, columns=["cluster id"])
    return whole_df, coor_clusters
    
def _split_in_cluster(coordinates: pd.DataFrame):
    if "x" not in coordinates.columns:
        raise Exception("'x' must be in the input coordinate columns.")
    if "y" not in coordinates.columns:
        raise Exception("'y' must be in the input coordinate columns.")

    _, coor_nums = np.unique(coordinates, axis=0, return_counts=True)
    unique_coors = coordinates.drop_duplicates().sort_values(by="x")
    large_num_coors = unique_coors[coor_nums>=np.percentile(coor_nums,60)]
    train_idx = np.random.choice(large_num_coors.index, size=len(coor_nums)//10)
    train_coors = unique_coors.loc[train_idx]
    test_coors = unique_coors.drop(train_idx)
    return train_coors, test_coors

def _split_train_test(xy_cluster: pd.DataFrame):
    if type(xy_cluster) is not pd.DataFrame:
        raise Exception("xy_cluster data is not pd.DataFrame.")

    np.random.seed(1000)
    all_split_sets = {}
    for cluster in np.sort(pd.unique(xy_cluster["cluster id"])):
        cluster_xy = xy_cluster.loc[xy_cluster["cluster id"]==cluster, ["x","y"]]
        out_cluster_xy = xy_cluster.loc[xy_cluster["cluster id"]!=cluster, ["x","y"]]
        cluster_train, cluster_test = _split_in_cluster(cluster_xy)
        all_split_sets[cluster] = {
            "train_in_cluster":cluster_train,
            "train_out_cluster":out_cluster_xy,
            "test_cluster":cluster_test
        }
    return all_split_sets

class SingleGrid:
    def __init__(self, cluster_method="GaussianMixture", cluster_num=10):
        self.cluster_num = cluster_num
        self.cluster_method = cluster_method

    def cluster_grids(self, input_dt: pd.DataFrame, target_dt: pd.Series):
        if type(input_dt) is not pd.DataFrame:
            raise Exception("Input data type is not pd.DataFrame.")
        if type(target_dt) is not pd.Series:
            raise Exception("Target data type is not pd.Series.")
        if not input_dt.index.equals(target_dt.index):
            raise Exception("Input and Output indexes are not equal.")
        if "x" not in input_dt.columns:
            raise Exception("'x' must be in the input data columns.")
        if "y" not in input_dt.columns:
            raise Exception("'y' must be in the input data columns.")

        return _cluster_coords(input_dt[["x", "y"]], self.cluster_method, self.cluster_num)

    def split_train_validation(self, input_dt: pd.DataFrame, whole_cluster: pd.DataFrame):
        if type(input_dt) is not pd.DataFrame:
            raise Exception("Input data type is not pd.DataFrame.")
        if type(whole_cluster) is not pd.DataFrame:
            raise Exception("Whole Cluster data type is not pd.DataFrame.")

        xy_cluster = input_dt[["x", "y"]].join(whole_cluster)
        return _split_train_test(xy_cluster)
        
class MultipleGrid(SingleGrid):
    def __init__(self, grid_scale, cluster_method="GaussianMixture", cluster_num=10):
        super().__init__(cluster_method, cluster_num)
        self.grid_scale = grid_scale

    def extract_center_data(self, tag_names: list, input_dt: np.ndarray):
        if type(input_dt) is not np.ndarray:
            raise Exception("Input data type is not np.array.")
        if input_dt.shape[1] != (len(tag_names)*(self.grid_scale**2)):
            raise Exception("Input data column number is inappropriate.")
            
        center_cell_id = (self.grid_scale**2)//2
        center_dt = input_dt[:,center_cell_id*len(tag_names):(center_cell_id+1)*len(tag_names)]
        return center_dt

    def cluster_grids(self, tag_names: list, input_dt: np.ndarray, target_dt: pd.Series):
        if type(input_dt) is not np.ndarray:
            raise Exception("Input data type is not np.array.")
        if input_dt.shape[1] != (len(tag_names)*(self.grid_scale**2)):
            raise Exception("Input data column number is inappropriate.")
        if type(target_dt) is not pd.Series:
            raise Exception("Target data type is not pd.Series.")
        if len(input_dt) != len(target_dt):
            raise Exception("The length of input data and target data are not equal.")

        center_dt = self.extract_center_data(tag_names, input_dt)
        center_frame = pd.DataFrame(center_dt, columns=tag_names, index=target_dt.index)
        return super().cluster_grids(center_frame, target_dt)

    def split_train_validation(self, tag_names: list, input_dt: np.ndarray, whole_cluster: pd.DataFrame):
        if type(input_dt) is not np.ndarray:
            raise Exception("Input data type is not np.array.")
        if input_dt.shape[1] != (len(tag_names)*(self.grid_scale**2)):
            raise Exception("Input data column number is inappropriate.")
        if type(whole_cluster) is not pd.DataFrame:
            raise Exception("Whole Cluster data type is not pd.DataFrame.")

        center_dt = self.extract_center_data(tag_names, input_dt)
        center_frame = pd.DataFrame(center_dt, columns=tag_names, index=whole_cluster.index)
        return super().split_train_validation(center_frame, whole_cluster)
