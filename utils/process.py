# 导入相关包
import copy
from matplotlib.pyplot import sca
from numpy.core.fromnumeric import size
import pandas as pd
import numpy as np

from sklearn import preprocessing
from sklearn.decomposition import PCA

def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    """
    数据处理
    :param data:数据
    :param n_in:输入特征个数
    :param n_out:目标值
    :param dropnan:是否删除 Nan 值 
    :return:
    """
    df = pd.DataFrame(data)
    n_vars = df.shape[1]  # n_vars 列数
    cols, names = list(), list()

    # 时间间隔跨度, 时间点个数，共 n_in 个
    # 首先添加当前时刻之前的时间点
    for i in range(n_in - 1, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j + 1, i)) for j in range(n_vars)]
    # 然后添加当前时刻
    cols.append(df)
    names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]

    # 添加 target 为未来 n_out 分钟后时刻的温度
    cols.append(df.shift(-n_out))
    names += [('var%d(t+%d)' % (j + 1, n_out)) for j in range(n_vars)]

    agg = pd.concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg

def process_pca(features):
    pca = PCA()
    pca.fit(features)

    sum = 0
    i = 0
    while True:
        sum += pca.explained_variance_ratio_[i]
        if sum >= 0.95: #取贡献值大于95%的部分
            break
        i += 1
    
    print(f'保留主元数目：{i + 1}')
    pca = PCA(i + 1)
    pca.fit(features)
    low_d = pca.transform(features) #降维

    # print(type(low_d))
    # print(f'low_d.shape: {low_d.shape}')
    # print(low_d[0])

    return low_d, pca

def process_data(data_path, n_in=1, n_out=1, validation_split = 0.2, dropnan=True, use_rnn = False):
    # 读取数据
    sensor_data = pd.read_csv(data_path, index_col=0)
    
    # 将耗电量进行 差分 处理
    data = copy.deepcopy(sensor_data)
    # DataFrame.shift()函数可以把数据移动指定的位数
    data['power_consumption']= data['power_consumption'] - data.shift(4)['power_consumption']
    data = data.round(2)
    
    # 确保所有数据是 float32 类型
    data = data.astype('float32')
    # print(data.shape)

    # 归一化特征
    scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    # 构建成监督学习数据集
    reframed = series_to_supervised(scaled_data, n_in, n_out, dropnan=True)    
    drop_col = [-1, -2, -3, -5, -6]
    reframed.drop(reframed.columns[drop_col], axis=1, inplace=True)
    
    # 把数据分为训练集和测试集
    values = reframed.values
    X, y = values[:, :-1], values[:, -1]
    if not use_rnn:
        X, pca = process_pca(X)
    else:
        pca = None

    train_num = int((1 - validation_split) * reframed.shape[0])
    train_X, train_y = X[:train_num], y[:train_num] 
    test_X, test_y = X[train_num:], y[train_num:]

    if use_rnn:
        train_X = train_X.reshape((train_X.shape[0], n_in, 6))
        test_X = test_X.reshape((test_X.shape[0], n_in, 6))

    return train_X, train_y, test_X, test_y, scaler, pca

def process_predict_data(data, n_in, n_out, scaler, pca, use_rnn = False):
    cols = ['outdoor_temperature','outdoor_humidity','indoor_temperature',
            'indoor_humidity','fan_status','power_consumption']
    df = pd.DataFrame(data, columns=cols)
    df['power_consumption'] = df['power_consumption'] - df.shift(4)['power_consumption']
    df = df.round(2)
    
    # 确保所有数据是 float32 类型
    df = df.astype('float32')
    scaled_data = scaler.transform(df)

    reframed = series_to_supervised(scaled_data, n_in, n_out)
    drop_col = [-1, -2, -3, -4, -5, -6]
    reframed.drop(reframed.columns[drop_col], axis=1, inplace=True)

    features = reframed.values

    if not use_rnn:
        features = pca.transform(features)
    else:
        features = features.reshape((features.shape[0], n_in, 6))

    return features

if __name__ == '__main__':
    data_path = 'dataset.csv'
    n_in, n_out, validation_split = 120, 6, 0.2
    use_rnn = False
    train_X, train_y, test_X, test_y, scaler, pca = process_data(data_path, n_in, n_out, 
                                                        validation_split, use_rnn)
    print(f'train_X.shape: {train_X.shape}')
    print(f'train_y.shape: {train_y.shape}')
    print(f'test_X.shape: {test_X.shape}')
    print(f'test_y.shape: {test_y.shape}')

    test = np.random.uniform(0, 1, size = (360, 6))
    features = process_predict_data(test, n_in, n_out, scaler, pca, use_rnn)
    print(f'features.shape: {features.shape}')