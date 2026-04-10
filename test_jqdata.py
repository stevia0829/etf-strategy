from jqdatasdk import *
auth('15871724276', '3825013rhRH')

if __name__ == '__main__':
    # 查看流量
    # 查询当日剩余可调用数据条数
    count = get_query_count()
    print(count)
