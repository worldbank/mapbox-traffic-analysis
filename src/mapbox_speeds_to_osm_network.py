import pandas as pd
import osmnx as ox
import argparse
import yaml
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()


def generate_auto_tt_network(city):
    '''Assigning Mapbox speeds to a OSM network'''
    with open('./configs/config.yaml') as f:
        configs = yaml.safe_load(f)
    config_city = configs['city'][city]
    north, south, east, west = config_city['north_south_east_west']
    speeds_file = config_city['speeds_file']
    crs = 'EPSG:4326'
    network_path = config_city['path_network']

    ### Get base network
    G1 = ox.graph_from_bbox(north, south, east, west, network_type='drive_service', simplify = False,
                            retain_all = True)
    G1 = ox.project_graph(G1)

    nodes, edges = ox.utils_graph.graph_to_gdfs(G1)
    nodes = nodes.to_crs(crs)
    edges = edges.to_crs(crs)
    nodes['x'] = nodes.geometry.apply(lambda x: x.x)
    nodes['y'] = nodes.geometry.apply(lambda x: x.y)

    ### Speeds file
    names = ["osm_start_node", "osm_end_node"]
    names.extend([f"speed_{i}" for i in range(1, 2017)])
    data = pd.read_csv(speeds_file, compression = 'gzip', header= None, names = names)
    data['start_node'] = data['osm_start_node']
    data['end_node'] = data['osm_end_node']
    data.set_index(['osm_start_node', 'osm_end_node'], inplace = True)

    ### Add speeds to the base network
    edges.reset_index(level = 2, inplace = True)
    idxs = set(['{}-{}'.format(x[0], x[1]) for x in data.index]).intersection(set(['{}-{}'.format(x[0], x[1]) for x in edges.index]))
    idxs_int = [(int(y[0]), int(y[1])) for y in [tuple(x.split('-')) for x in idxs]]
    # TODO: Change with the specific time
    edges.loc[idxs_int, 'mb_speed'] = data.loc[idxs_int, 'speed_973']
    edges['imputed'] = 1
    edges.loc[idxs_int, 'imputed'] = 0


    print('Mapbox is providing information for {}% of the links. The rest of the data will be imputed'.format(len(edges[edges['mb_speed'].notnull()])/len(edges)))
    print('The following table shows the percentage of imputation per highway type')
    print((edges[edges['mb_speed'].isnull()]['highway'].value_counts()/edges['highway'].value_counts()).sort_values())

    sns.boxplot(data=edges, x="mb_speed", y="highway")
    plt.show()

    # TODO: Decide if we are pursuing the imputation
    # ### Impute missing speeds
    # def quantile(data, variable, quantile):
    #     return data[variable].quantile(quantile)
    #
    # # generate a dictionary with the imputation speed per highway type. Types for which we do not have information for, must be manually imputed
    # # in our case, imputation is being done using the 75% percentile
    # for_imputation = edges[edges['mb_speed'].notnull()].groupby('highway').apply(quantile, 'mb_speed', 0.5).to_dict()
    # for_imputation['crossing'] = 1.6 #pedestrian
    # for_imputation['disused'] = 1.6 #pedestrian
    # for_imputation['services'] = 10
    # for_imputation['rest_area'] = 10
    # for_imputation['busway'] = 1
    #
    # edges.loc[edges['mb_speed'].isnull(), 'mb_speed'] = edges.loc[edges['mb_speed'].isnull()]['highway'].apply(lambda x: for_imputation[x])
    # edges['tt'] = ((edges['length']/1000)/edges['mb_speed'])*60 #travel time should be in minutes
    # sns.boxplot(data=edges, x="mb_speed", y="highway")
    # plt.show()
    edges.to_csv(network_path + '{}_edges_speeds.csv')
    nodes.to_csv(network_path + '{}_nodes.csv')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--city', type = str, help = 'City to explore')
    args = parser.parse_args()

    city = args.city
    generate_auto_tt_network(city)
